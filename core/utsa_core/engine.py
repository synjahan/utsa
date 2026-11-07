"""Policy-filtered projection, actual MeTTa inference, evidence and action intents."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import asdict
from pathlib import Path

from .memory import MemoryPort
from .model import Actor, Bridge, Scope, epoch

RULES = Path(__file__).with_name("rules.metta").read_text()
RULE_VERSION = hashlib.sha256(RULES.encode()).hexdigest()


def token(value: str) -> str:
    """Opaque symbols: text can never inject code, variables, or control facts."""
    return "s" + hashlib.sha256(value.encode()).hexdigest()


def digest(value) -> str:
    """Stable short hash of any JSON-serialisable value, used for revision-scoped ids."""
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class HyperonRuntime:
    name = "hyperon-0.2.10"

    def run(self, facts: list[str], queries: list[str]) -> list[list[str]]:
        """Evaluate the queries against the facts and return one list of proofs per query."""
        from hyperon import MeTTa

        metta = MeTTa()
        metta.run(RULES + "\n" + "\n".join(facts))
        answers = []
        for query in queries:
            result = metta.run(f"!(collapse ({query}))")
            if len(result) != 1 or len(result[0]) != 1:
                raise RuntimeError("unexpected MeTTa result shape")
            atoms = [str(a) for a in result[0][0].get_children()]
            if any("Error" in a for a in atoms):
                raise RuntimeError("MeTTa evaluation failed")
            answers.append(atoms)
        return answers


class PeTTaRuntime:
    """Runs the exact same rules on an explicitly configured PeTTa checkout.

    No shell interpolation, network access, Python interop, or model calls in
    this adapter. The runner path is trusted operator configuration.
    """

    name = "petta"

    def __init__(self, runner: str):
        self.runner = str(Path(runner).resolve(strict=True))

    def run(self, facts: list[str], queries: list[str]) -> list[list[str]]:
        """Evaluate the queries against the facts and return one list of proofs per query."""
        if not queries:
            return []
        code = RULES + "\n" + "\n".join(facts)
        code += "\n" + "\n".join(f"!(collapse ({q}))" for q in queries) + "\n"
        with tempfile.TemporaryDirectory(prefix="utsa-petta-") as directory:
            path = Path(directory) / "query.metta"
            path.write_text(code)
            result = subprocess.run(
                ["sh", self.runner, str(path), "--silent"],
                text=True,
                capture_output=True,
                timeout=30,
            )
        # PeTTa can exit zero after startup errors: stderr must also be clear.
        if result.returncode or result.stderr.strip():
            raise RuntimeError("PeTTa startup or evaluation failed: " + result.stderr[:2000])
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if len(lines) != len(queries):
            raise RuntimeError("unexpected PeTTa result count")
        return [self._parse(line) for line in lines]

    @staticmethod
    def _parse(line: str) -> list[str]:
        # The output grammar is deliberately tiny: constructor names and opaque
        # symbols only. Quotes, grounded values, and arbitrary forms fail closed.
        if not re.fullmatch(r"[a-zA-Z0-9_()\s-]+", line):
            raise RuntimeError("unexpected PeTTa output")
        tokens = re.findall(r"\(|\)|[^\s()]+", line)

        def read(index):
            """Parse one atom starting at this token; return it and the next token index."""
            if index >= len(tokens):
                raise RuntimeError("incomplete PeTTa output")
            value = tokens[index]
            if value != "(":
                if value == ")":
                    raise RuntimeError("invalid PeTTa output")
                return value, index + 1
            items, index = [], index + 1
            while index < len(tokens) and tokens[index] != ")":
                item, index = read(index)
                items.append(item)
            if index >= len(tokens):
                raise RuntimeError("unclosed PeTTa output")
            return items, index + 1

        value, end = read(0)
        if end != len(tokens) or not isinstance(value, list):
            raise RuntimeError("invalid PeTTa result")

        def show(item):
            """Render a parsed PeTTa value back into MeTTa text, nesting lists in parentheses."""
            return "(" + " ".join(show(x) for x in item) + ")" if isinstance(item, list) else item

        answer = [show(item) for item in value]
        if any("Error" in item for item in answer):
            raise RuntimeError("MeTTa evaluation failed")
        return answer


class Utsa:
    def __init__(self, memory: MemoryPort, bridges: tuple[Bridge, ...] = (), runtime=None):
        self.memory = memory  # Exactly one provider; no hidden fallback store.
        self.bridges = bridges
        if len({b.evidence_id for b in bridges}) != len(bridges):
            raise ValueError("bridge evidence IDs must be unique")
        configured = os.environ.get("UTSA_PETTA_RUNNER")
        self.runtime = runtime or (PeTTaRuntime(configured) if configured else HyperonRuntime())

    def _projection(self, records: list[dict], now: int):
        facts = [f"(Now {now})"]
        by_token = {}
        bridges = {}
        for r in records:
            rid, owner = token(r["id"]), token(r["owner"])
            by_token[rid] = r
            facts += [
                f"(Record {rid} {owner} {r['kind']})",
                f"(Eligible {rid})",
                f"(Entity {rid} {token(r['entity']['id'])})",
                f"(Domain {rid} {token(r['domain'])})",
            ]
            conditions = r["conditions"]
            state = "unresolved" if conditions["unresolved"] else "clear"
            facts.append(f"(Conditions {rid} {conditions['mode']} {conditions['terms']} {state})")
            for topic in r["topics"]:
                facts.append(f"(Topic {rid} {token(topic)})")
            for skill in r["requires"]:
                facts.append(f"(Requires {rid} {token(skill)})")
            for skill in r["provides"]:
                facts.append(f"(Provides {rid} {token(skill)})")
            if r["capability_evidence"] == "confirmed":
                facts.append(f"(Confirmed {rid})")
            av = r["availability"]
            if av["confirmed"]:
                facts.append(f"(Available {rid})")
            facts += [
                f"(Window {rid} {epoch(av['from'])} {epoch(av['until'])})",
                f"(Effort {rid} {av['hours']})",
            ]
            if r["action"].strip():
                facts.append(f"(Actionable {rid})")
        # Reviewed mapping facts are projected without precomputing pair fits.
        # MeTTa joins capability, requirement, and both domains.
        for bridge in self.bridges:
            bt = token(digest(asdict(bridge)))
            bridges[bt] = bridge
            facts.append(
                f"(Bridge {token(bridge.capability)} {token(bridge.requirement)} "
                f"{token(bridge.source_domain)} {token(bridge.target_domain)} {bt})"
            )
        return sorted(set(facts)), by_token, bridges

    def discover(self, trigger_id: str, scope: Scope, now: int) -> list[dict]:
        """Return every relation the trigger record takes part in, visible in this scope now."""
        with self.memory.transaction():
            return self._discover(trigger_id, scope, now)

    def _discover(self, trigger_id: str, scope: Scope, now: int) -> list[dict]:
        """Find every relation the trigger record takes part in, and record each one."""
        records = self.memory.visible(scope, now)
        # Utsa's own identity can never become a match candidate.
        records = [
            r for r in records if r["owner"] != scope.agent and r["entity"]["id"] != scope.agent
        ]
        trigger = next((r for r in records if r["id"] == trigger_id), None)
        if trigger is None:
            return []  # No distinction between missing and inaccessible.
        facts, indexed, bridges = self._projection(records, now)
        output = self.runtime.run(facts, self._queries(trigger_id, records))
        results = {}
        for proof in (p for batch in output for p in batch):
            kind, a, b, evidence = self._parse(proof)
            first, second = indexed[a], indexed[b]
            if kind == "SharedInterest":
                first, second = sorted((first, second), key=lambda r: r["id"])
            bridge = self._bridge(bridges, evidence, proof, first, second)
            relation = self._relation(kind, first, second, bridge, evidence, scope, now)
            if kind == "ComplementaryCapability":
                relation["blockers"] = sorted(set(self.runtime.run(facts, [f"blocker {a} {b}"])[0]))
            self.memory.save_relationship(relation)
            results[relation["id"]] = relation
        return sorted(results.values(), key=lambda r: (r["type"], r["id"]))

    @staticmethod
    def _queries(trigger_id: str, records: list[dict]) -> list[str]:
        """One interest query and both directions of complement and opportunity per pair."""
        queries = []
        for other in records:
            if other["id"] == trigger_id:
                continue
            a, b = token(trigger_id), token(other["id"])
            queries.append(f"interest {a} {b}")
            queries += [f"{fn} {a} {b}" for fn in ("complement", "opportunity")]
            queries += [f"{fn} {b} {a}" for fn in ("complement", "opportunity")]
        return queries

    @staticmethod
    def _parse(proof: str) -> tuple[str, str, str, str]:
        """Split a proof into its claim kind, the two record tokens and the evidence token."""
        parts = proof.strip("()").split()
        kind, a, b = parts[:3]
        if kind not in {"SharedInterest", "ComplementaryCapability", "GenuineOpportunity"}:
            raise RuntimeError("unexpected inference")
        return kind, a, b, parts[-1]

    @staticmethod
    def _bridge(bridges: dict, evidence: str, proof: str, first: dict, second: dict):
        """The reviewed bridge behind a claim, a synthetic direct bridge, or None for interest."""
        if evidence != "direct":
            return bridges.get(evidence)
        capability_token = proof.strip("()").split()[3]
        capability = next(s for s in second["provides"] if token(s) == capability_token)
        return Bridge(
            capability,
            capability,
            "direct:" + capability,
            "The offered capability exactly meets the stated requirement.",
            "Capability is a participant claim, not an independent skill certification.",
            second["domain"],
            first["domain"],
        )

    @staticmethod
    def _relation(
        kind: str, first: dict, second: dict, bridge, evidence: str, scope: Scope, now: int
    ) -> dict:
        """Assemble the stored relation for one claim, including its revision-scoped id."""
        explanation = (
            bridge.explanation
            if bridge
            else (
                "Both contributions explicitly name the same interest; "
                "this makes no capability or availability claim."
            )
        )
        topic = (
            next((t for t in first["topics"] if token(t) == evidence), None)
            if kind == "SharedInterest"
            else None
        )
        relation = {
            "type": kind,
            "supports": [{"id": r["id"], "revision": r["revision"]} for r in (first, second)],
            "scope": asdict(scope),
            "rule_version": RULE_VERSION,
            "bridge_version": digest(asdict(bridge)) if bridge else None,
            "evidence_id": bridge.evidence_id if bridge else "topic:" + topic,
            "explanation": explanation,
            "limitation": (
                bridge.limitation
                if bridge
                else "Shared interest alone does not establish a useful collaboration."
            ),
            "cross_domain": first["domain"] != second["domain"],
            "age_gap_seconds": abs(epoch(first["created_at"]) - epoch(second["created_at"])),
            "observed_at": now,
            "valid_until": min(
                epoch(r[k]) for r in (first, second) for k in ("valid_until", "fresh_until")
            ),
            "state": "candidate" if kind == "GenuineOpportunity" else "discovered",
        }
        relation["blockers"] = []
        if kind == "GenuineOpportunity":
            relation["valid_until"] = min(
                relation["valid_until"],
                epoch(first["availability"]["until"]),
                epoch(second["availability"]["until"]),
            )
        # Observations at later times reuse the same revision-specific identity.
        identity = {
            k: relation[k]
            for k in (
                "type",
                "supports",
                "scope",
                "rule_version",
                "bridge_version",
                "evidence_id",
            )
        }
        relation["id"] = "rel:" + digest(identity)
        if kind == "GenuineOpportunity":
            relation["explanation"] += (
                " Both records permit discovery here, availability windows overlap, "
                "capacity covers the request, and the supported conditions agree. "
                "Both owners still need to choose an introduction."
            )
        return relation

    def _current(self, key: str, scope: Scope, now: int) -> dict:
        try:
            relation = self.memory.get_relationship(key)
        except KeyError:
            raise PermissionError("relationship not available") from None
        if relation["scope"] != asdict(scope):
            raise PermissionError("relationship not available")
        current = self._discover(relation["supports"][0]["id"], scope, now)
        result = next((r for r in current if r["id"] == key), None)
        if result is None:
            raise PermissionError("relationship not available")
        return result

    def preview(self, key: str, viewer: Actor, scope: Scope, now: int) -> dict:
        """Return the minimised, permission-checked view of one relation for one actor."""
        with self.memory.transaction():
            relation = self._current(key, scope, now)
            records = {r["id"]: r for r in self.memory.visible(scope, now)}
            sources = [records[s["id"]] for s in relation["supports"]]
            if (
                viewer.subject not in {r["owner"] for r in sources}
                or viewer.container != scope.container
            ):
                raise PermissionError("suggestion not available")
            if not all(self.memory.preview_allowed(r, viewer, scope, now) for r in sources):
                raise PermissionError("suggestion not available")
            # Only an explicitly approved summary. Raw quotes, provenance links,
            # counterpart IDs, and other people's private decisions stay internal.
            return {
                "suggestion_id": key,
                "type": relation["type"],
                "summaries": [r["permitted_summary"] for r in sources],
                "explanation": relation["explanation"],
                "limitation": relation["limitation"],
                "blockers": relation["blockers"],
                "next_action": (
                    "Consider an introduction"
                    if relation["type"] == "GenuineOpportunity"
                    else "Explore the evidence; no introduction is ready"
                ),
            }

    def decide(self, key: str, actor: Actor, scope: Scope, accept: bool, now: int):
        """Record an actor's acceptance or decline of one relation at its current revisions."""
        with self.memory.transaction():
            relation = self._current(key, scope, now)
            if relation["type"] != "GenuineOpportunity":
                raise ValueError("only an actionable opportunity can request an introduction")
            self.preview(key, actor, scope, now)
            self.memory.decide(actor, relation, accept, now)

    def connection_intent(self, key: str, scope: Scope, now: int) -> dict | None:
        """Return the undelivered introduction intent once both owners have accepted, else None."""
        with self.memory.transaction():
            relation = self._current(key, scope, now)
            if relation["type"] != "GenuineOpportunity":
                return None
            records = self.memory.visible(scope, now)
            selected = [r for s in relation["supports"] for r in records if r["id"] == s["id"]]
            facts, _, _ = self._projection(records, now)
            for source, target in (selected, selected[::-1]):
                # Revoke permission to view a suggestion -> no stale action intent.
                viewer = Actor(source["owner"], scope.container)
                if not all(self.memory.preview_allowed(r, viewer, scope, now) for r in selected):
                    return None
                if self.memory.approved(key, source["owner"]):
                    facts.append(f"(Accepted {token(source['id'])} {token(target['id'])})")
            n, o = (token(s["id"]) for s in relation["supports"])
            if not self.runtime.run(facts, [f"connection-ready {n} {o}"])[0]:
                return None
            return {
                "idempotency_key": key,
                "state": "ready-for-host-authorization",
                "action": "request-permissioned-introduction",
                "source_revisions": relation["supports"],
                "scope": asdict(scope),
                "delivered": False,
                "requires": [
                    "host identity resolution",
                    "explicit contact-field disclosure grants",
                    "authorization recheck at delivery",
                    "delivery receipt",
                ],
            }
