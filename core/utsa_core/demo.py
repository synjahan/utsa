"""Offline fixture CLI. Identity arguments here are test identities, not login."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import Utsa
from .memory import SQLiteMemory
from .model import Actor, Bridge, Scope, epoch


def seed(memory, record, target, now):
    """Store a fixture record and grant discovery for it in the target container."""
    actor = Actor(record["owner"], record["origin"]["container"])
    memory.put(actor, record, now)
    memory.grant(
        actor,
        record["id"],
        record["revision"],
        "utsa",
        target,
        "discovery",
        "discover",
        True,
        epoch(record["valid_until"]),
        now,
    )


def main():
    """Command-line entry point for the demo scenarios."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=["sprint-old", "sprint-new", "cross-domain"])
    parser.add_argument("--db", required=True)
    parser.add_argument("--fixture", required=True)
    args = parser.parse_args()
    fixture = json.loads(Path(args.fixture).read_text())
    memory = SQLiteMemory(args.db)
    target = fixture["target_container"]
    try:
        if args.scenario == "sprint-old":
            seed(memory, fixture["offer"], target, epoch(fixture["old_time"]))
            print(
                json.dumps(
                    {
                        "stored": fixture["offer"]["id"],
                        "revision": 1,
                        "matches": [],
                        "fixture_kind": fixture["fixture_kind"],
                    },
                    indent=2,
                )
            )
        elif args.scenario == "sprint-new":
            now = epoch(fixture["new_time"])
            seed(memory, fixture["need"], target, now)
            print(
                json.dumps(
                    Utsa(memory).discover(fixture["need"]["id"], Scope("utsa", target), now),
                    indent=2,
                )
            )
        else:
            now = epoch(fixture["time"])
            for record in fixture["contributions"]:
                seed(memory, record, target, now)
            engine = Utsa(memory, (Bridge(**fixture["bridge"]),))
            print(
                json.dumps(
                    engine.discover(fixture["contributions"][0]["id"], Scope("utsa", target), now),
                    indent=2,
                )
            )
    finally:
        memory.close()


if __name__ == "__main__":
    main()
