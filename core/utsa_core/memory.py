"""One authoritative store. MeTTa projections are transient and disposable.

SQLite is the local reference adapter, not an additional Hives memory service.
Actor/Scope values are trusted only inside this local process API. A live adapter
must derive them from authenticated host identity, never an incoming JSON body.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Protocol

from .model import Actor, Scope, epoch, validate


class ConflictError(ValueError):
    pass


Conflict = ConflictError  # Backwards-compatible alias.


class MemoryPort(Protocol):
    """Required host contract, not an assertion about any platform API."""

    authority_id: str

    def transaction(self):
        """Run a block of writes atomically."""
        ...

    def visible(self, scope: Scope, now: int) -> list[dict]:
        """Return the records this scope may use for discovery right now."""
        ...

    def save_relationship(self, relationship: dict) -> None:
        """Store one relation under its revision-scoped id; an existing row is left unchanged."""
        ...

    def get_relationship(self, key: str) -> dict:
        """Return a stored relation by id; raise KeyError if there is none."""
        ...

    def approved(self, key: str, owner: str) -> bool:
        """Whether this owner's latest decision on the relation is an acceptance."""
        ...

    def decide(self, actor: Actor, relationship: dict, accept: bool, now: int) -> None:
        """Append an owner's decision on a relation."""
        ...

    def preview_allowed(self, record: dict, viewer: Actor, scope: Scope, now: int) -> bool:
        """Whether this principal may see the record's approved summary here."""
        ...


class SQLiteMemory:
    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(str(path), isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=DELETE")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS records (
            id TEXT, revision INTEGER, recorded_at INTEGER, payload TEXT NOT NULL,
            PRIMARY KEY(id, revision));
          CREATE TABLE IF NOT EXISTS grants (
            seq INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT, revision INTEGER,
            principal TEXT, container TEXT, purpose TEXT, action TEXT,
            allowed INTEGER, expires INTEGER, recorded_at INTEGER);
          CREATE TABLE IF NOT EXISTS pauses (
            owner TEXT PRIMARY KEY, paused INTEGER, recorded_at INTEGER);
          CREATE TABLE IF NOT EXISTS relationships (
            id TEXT PRIMARY KEY, payload TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS decisions (
            seq INTEGER PRIMARY KEY AUTOINCREMENT, relationship_id TEXT,
            owner TEXT, accepted INTEGER, recorded_at INTEGER);
          CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
        """)
        self.authority_id = "sqlite:" + str(Path(path).resolve())

    def close(self):
        """Close the underlying database connection."""
        self.db.close()

    @contextmanager
    def transaction(self):
        # One consistent snapshot and serialized updates, including final recheck.
        """Run a block of writes atomically."""
        if self.db.in_transaction:
            yield
            return
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def _clock(self, now: int):
        previous = self.db.execute("SELECT value FROM meta WHERE key='clock'").fetchone()
        if previous and now < int(previous[0]):
            raise ValueError("operational clock cannot move backwards")
        self.db.execute("INSERT OR REPLACE INTO meta VALUES ('clock', ?)", (str(now),))

    def latest(self, record_id: str) -> dict:
        """Return the current revision of a record; raise KeyError if there is none."""
        row = self.db.execute(
            "SELECT payload FROM records WHERE id=? ORDER BY revision DESC LIMIT 1", (record_id,)
        ).fetchone()
        if row is None:
            raise KeyError(record_id)
        return json.loads(row[0])

    def put(self, actor: Actor, record: dict, now: int):
        """Validate and store a new revision of a record under its owner's authority."""
        validate(record)
        if record["owner"] != actor.subject or record["origin"]["container"] != actor.container:
            raise PermissionError("contribution owner and origin must match authenticated actor")
        if not record["id"].startswith(actor.container + ":"):
            raise ValueError("record id must be namespaced by its origin container")
        if record["entity"]["type"] == "person" and record["entity"]["id"] != actor.subject:
            raise PermissionError("person contribution must describe its authenticated owner")
        if epoch(record["created_at"]) > now:
            raise ValueError("future-dated contribution")
        with self.transaction():
            self._clock(now)
            paused = self.db.execute(
                "SELECT paused FROM pauses WHERE owner=?", (actor.subject,)
            ).fetchone()
            if paused and paused[0] and record["status"] != "withdrawn":
                raise PermissionError("paused owner cannot create active contributions")
            try:
                previous = self.latest(record["id"])
            except KeyError:
                previous = None
            if previous == record:
                return  # Idempotent ingestion.
            if record["revision"] != (previous["revision"] + 1 if previous else 1):
                raise ConflictError("expected next revision")
            if previous:
                for field in ("owner", "origin", "entity", "created_at"):
                    if previous[field] != record[field]:
                        raise ConflictError(f"immutable provenance changed: {field}")
            self.db.execute(
                "INSERT INTO records VALUES (?,?,?,?)",
                (record["id"], record["revision"], now, json.dumps(record, sort_keys=True)),
            )

    def grant(
        self,
        actor: Actor,
        record_id: str,
        revision: int,
        principal: str,
        container: str,
        purpose: str,
        action: str,
        allowed: bool,
        expires: int,
        now: int,
    ):
        """Record a permission decision for one record revision, principal, purpose and action."""
        if action not in {"discover", "preview"} or type(allowed) is not bool:
            raise ValueError("unsupported permission")
        with self.transaction():
            self._clock(now)
            record = self.latest(record_id)
            if actor.subject != record["owner"] or actor.container != record["origin"]["container"]:
                raise PermissionError("only the authenticated source owner can grant access")
            if revision != record["revision"] or expires <= now:
                raise ConflictError("permission must reference current revision and future expiry")
            self.db.execute(
                """INSERT INTO grants
                   (record_id, revision, principal, container, purpose,
                    action, allowed, expires, recorded_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    record_id,
                    revision,
                    principal,
                    container,
                    purpose,
                    action,
                    int(allowed),
                    expires,
                    now,
                ),
            )

    def _allowed(
        self, record: dict, principal: str, container: str, purpose: str, action: str, now: int
    ) -> bool:
        row = self.db.execute(
            """SELECT allowed, expires FROM grants
               WHERE record_id=? AND revision=? AND principal=?
                 AND container=? AND purpose=? AND action=?
               ORDER BY seq DESC LIMIT 1""",
            (record["id"], record["revision"], principal, container, purpose, action),
        ).fetchone()
        return bool(row and row[0] and now < row[1])

    def pause(self, actor: Actor, paused: bool, now: int):
        """Pause or resume discovery for everything this actor owns."""
        if type(paused) is not bool:
            raise ValueError("paused must be Boolean")
        with self.transaction():
            self._clock(now)
            self.db.execute(
                "INSERT OR REPLACE INTO pauses VALUES (?,?,?)", (actor.subject, int(paused), now)
            )

    def visible(self, scope: Scope, now: int) -> list[dict]:
        """Return the records this scope may use for discovery right now."""
        self._clock(now)
        rows = self.db.execute("""SELECT r.payload FROM records r
          JOIN (SELECT id,MAX(revision) revision FROM records GROUP BY id) latest
          ON r.id=latest.id AND r.revision=latest.revision""")
        result = []
        for row in rows:
            record = json.loads(row[0])
            paused = self.db.execute(
                "SELECT paused FROM pauses WHERE owner=?", (record["owner"],)
            ).fetchone()
            if (
                record["status"] == "active"
                and not (paused and paused[0])
                and epoch(record["valid_from"]) <= now < epoch(record["valid_until"])
                and now < epoch(record["fresh_until"])
                and self._allowed(
                    record, scope.agent, scope.container, scope.purpose, "discover", now
                )
            ):
                result.append(record)
        return sorted(result, key=lambda r: r["id"])

    def preview_allowed(self, record: dict, viewer: Actor, scope: Scope, now: int) -> bool:
        """Whether this principal may see the record's approved summary here."""
        return viewer.container == scope.container and self._allowed(
            record, viewer.subject, scope.container, scope.purpose, "preview", now
        )

    def save_relationship(self, relationship: dict):
        """Store one relation under its revision-scoped id; an existing row is left unchanged."""
        # Materialized inference metadata lives in the same authority. No quotes,
        # contact fields, or duplicate source payloads are copied into this row.
        self.db.execute(
            "INSERT OR IGNORE INTO relationships VALUES (?,?)",
            (relationship["id"], json.dumps(relationship, sort_keys=True)),
        )

    def get_relationship(self, key: str) -> dict:
        """Return a stored relation by id; raise KeyError if there is none."""
        row = self.db.execute("SELECT payload FROM relationships WHERE id=?", (key,)).fetchone()
        if row is None:
            raise KeyError(key)
        return json.loads(row[0])

    def approved(self, key: str, owner: str) -> bool:
        """Whether this owner's latest decision on the relation is an acceptance."""
        row = self.db.execute(
            """SELECT accepted FROM decisions
               WHERE relationship_id=? AND owner=?
               ORDER BY seq DESC LIMIT 1""",
            (key, owner),
        ).fetchone()
        return bool(row and row[0])

    def decide(self, actor: Actor, relationship: dict, accept: bool, now: int):
        """Append an owner's decision on a relation."""
        if type(accept) is not bool:
            raise ValueError("accept must be Boolean")
        self._clock(now)
        if actor.container != relationship["scope"]["container"]:
            raise PermissionError("wrong decision workspace")
        owners = {self.latest(s["id"])["owner"] for s in relationship["supports"]}
        if actor.subject not in owners:
            raise PermissionError("only a source owner may decide")
        # This prototype approves an introduction intent only. It has no identity
        # directory and cannot reveal contact details or mark delivery complete.
        self.db.execute(
            "INSERT INTO decisions(relationship_id,owner,accepted,recorded_at) VALUES (?,?,?,?)",
            (relationship["id"], actor.subject, int(accept), now),
        )

    def delete(self, actor: Actor, record_id: str, now: int):
        """Local erasure, including derived relationships; backups are host scope."""
        with self.transaction():
            self._clock(now)
            record = self.latest(record_id)
            if actor.subject != record["owner"] or actor.container != record["origin"]["container"]:
                raise PermissionError("only owner can delete")
            keys = [
                r[0]
                for r in self.db.execute("SELECT id,payload FROM relationships")
                if any(s["id"] == record_id for s in json.loads(r[1])["supports"])
            ]
            for key in keys:
                self.db.execute("DELETE FROM decisions WHERE relationship_id=?", (key,))
                self.db.execute("DELETE FROM relationships WHERE id=?", (key,))
            self.db.execute("DELETE FROM grants WHERE record_id=?", (record_id,))
            self.db.execute("DELETE FROM records WHERE id=?", (record_id,))
