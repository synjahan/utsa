"""End-to-end consent loop smoke test, v2 (suggested patch, 6 Nov 2026).

Changes from v1 (review findings A1, A2):
  * A failed check sets a nonzero exit status; the script runs every check, then
    exits 1 if any failed, so automation cannot mistake FAIL for success.
  * The preview check is strict: the preview may contain only the fields the
    engine documents (suggestion_id, type, summaries, explanation, limitation,
    blockers, next_action); the summaries must be exactly the approved
    permitted_summary texts; and none of the counterpart's identifying fields
    (owner, entity id, origin container, source_ref, verbatim text) may appear
    anywhere in the serialized preview.
  * A GAP step shows, with a synthetic record, that an approved summary which
    itself names a person passes through unchanged. That is decision 4
    (owner or host must review summaries); it is reported, not counted as FAIL.

Run from core/:  .venv/bin/python ../smoke_loop_v2.py
Set SMOKE_FORCE_FAIL=1 to prove the nonzero exit path.
"""
import copy
import json
import os
import sys
import tempfile
from pathlib import Path

from utsa_core.demo import seed
from utsa_core.engine import Utsa
from utsa_core.memory import SQLiteMemory
from utsa_core.model import Actor, Scope, epoch

FAILURES: list[str] = []
ALLOWED_PREVIEW_KEYS = {"suggestion_id", "type", "summaries", "explanation",
                        "limitation", "blockers", "next_action"}


def step(label: str, ok: bool) -> None:
    print(("PASS " if ok else "FAIL ") + label)
    if not ok:
        FAILURES.append(label)


def identifying_strings(record: dict) -> set[str]:
    """Everything about a record that could identify its owner, except the
    approved summary, which is the only text allowed to leave the store."""
    out = {record["owner"], record["entity"]["id"], record["origin"]["container"],
           record["origin"]["source_ref"], record["verbatim"]}
    out.update(v for v in record.get("contact", {}).values() if isinstance(v, str))
    return {s for s in out if s}


def grant_preview(store, record, viewer, now, allow=True):
    store.grant(Actor(record["owner"], record["origin"]["container"]), record["id"],
                record["revision"], viewer, "pilot", "discovery", "preview", allow,
                epoch(record["valid_until"]), now)


def main() -> int:
    f = json.loads(Path("fixtures/sprint_reconstruction.json").read_text())
    offer, need = f["offer"], f["need"]
    store = SQLiteMemory(Path(tempfile.mkdtemp()) / "loop.sqlite")
    engine = Utsa(store)
    now = epoch(f["new_time"])
    scope = Scope("utsa", "pilot")
    for r in (offer, need):
        seed(store, r, "pilot", now)

    opp = [r for r in engine.discover(need["id"], scope, now) if r["type"] == "GenuineOpportunity"]
    step("1 discover finds exactly one GenuineOpportunity", len(opp) == 1)
    if not opp:
        return finish(store)
    key = opp[0]["id"]

    try:
        engine.preview(key, Actor("person-a", "pilot"), scope, now)
        step("2 preview blocked without preview grant", False)
    except PermissionError:
        step("2 preview blocked without preview grant", True)

    for r in (offer, need):
        for viewer in ("person-a", "person-b"):
            grant_preview(store, r, viewer, now)

    p = engine.preview(key, Actor("person-a", "pilot"), scope, now)
    serialized = json.dumps(p)
    leaked = sorted(s for s in identifying_strings(offer) - {offer["permitted_summary"]} if s in serialized)
    # In this fixture the verbatim text equals the permitted summary, so it is
    # excluded from the leak set above; the GAP step below covers that case.
    step("3a preview has only the documented fields", set(p) == ALLOWED_PREVIEW_KEYS)
    step("3b preview summaries are exactly the approved texts",
         sorted(p["summaries"]) == sorted([offer["permitted_summary"], need["permitted_summary"]]))
    step(f"3c no counterpart identifier in preview (leaked: {leaked or 'none'})", not leaked)

    engine.decide(key, Actor("person-a", "pilot"), scope, True, now)
    step("4 one yes is not enough", engine.connection_intent(key, scope, now) is None)
    engine.decide(key, Actor("person-b", "pilot"), scope, True, now)
    intent = engine.connection_intent(key, scope, now)
    step("5 both yes -> intent, delivered=False", bool(intent) and intent["delivered"] is False)
    if intent:
        print("   intent.requires =", intent["requires"])

    grant_preview(store, offer, "person-a", now + 1, allow=False)
    step("6 revoking preview kills the intent", engine.connection_intent(key, scope, now + 1) is None)
    grant_preview(store, offer, "person-a", now + 2, allow=True)
    back = engine.connection_intent(key, scope, now + 2) is not None
    print(f"NOTE 7 restoring preview {'REACTIVATES' if back else 'does not reactivate'} earlier acceptances (open product decision 2)")

    for owner_id in ("person-c", "person-d"):
        n = copy.deepcopy(need)
        n["id"] = f"sprint-{owner_id}:need"; n["owner"] = owner_id; n["entity"]["id"] = owner_id
        n["origin"]["container"] = f"sprint-{owner_id}"; n["availability"]["hours"] = 4
        seed(store, n, "pilot", now + 3)
    hits = [r for r in engine.discover(offer["id"], scope, now + 3) if r["type"] == "GenuineOpportunity"]
    print(f"NOTE 8 one 4h offer yields {len(hits)} simultaneous opportunities (candidate capacity, not reserved; open product decision 3)")

    # GAP: an approved summary that itself identifies a person is passed through unchanged.
    leaky = copy.deepcopy(offer)
    leaky["id"] = "sprint-e:offer"; leaky["owner"] = "person-e"; leaky["entity"]["id"] = "person-e"
    leaky["origin"]["container"] = "sprint-e"; leaky["origin"]["source_ref"] = "fixture:sprint-e:offer"
    leaky["permitted_summary"] = "Ask for Bob Example, bob.example@example.org, four hours of bot testing."
    leaky["verbatim"] = leaky["permitted_summary"]
    seed(store, leaky, "pilot", now + 4)
    for viewer in ("person-a", "person-e"):
        grant_preview(store, leaky, viewer, now + 4)
        grant_preview(store, need, viewer, now + 4)
    pair = [r for r in engine.discover(leaky["id"], scope, now + 4)
            if r["type"] == "GenuineOpportunity" and {s["id"] for s in r["supports"]} == {leaky["id"], need["id"]}]
    shown = engine.preview(pair[0]["id"], Actor("person-a", "pilot"), scope, now + 4) if pair else None
    passthrough = bool(shown) and "bob.example@example.org" in json.dumps(shown)
    print(f"GAP 9 an identifying approved summary is shown unchanged: {passthrough} (open product decision 4; the core does not police summary content)")

    if os.environ.get("SMOKE_FORCE_FAIL"):
        step("X forced failure to prove nonzero exit", False)
    return finish(store)


def finish(store) -> int:
    store.close()
    if FAILURES:
        print(f"\n{len(FAILURES)} check(s) FAILED: " + "; ".join(FAILURES))
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
