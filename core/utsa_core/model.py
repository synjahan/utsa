"""Shared typed contribution vocabulary; host identity never comes from prose."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

SCHEMA = json.loads(Path(__file__).with_name("contribution.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def epoch(value: str) -> int:
    """Parse an ISO-8601 UTC timestamp into integer seconds."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset().total_seconds() != 0 or dt.microsecond:
        raise ValueError("timestamps must be UTC with whole-second precision")
    return int(dt.timestamp())


def timestamp(value: int) -> str:
    """Format integer seconds as an ISO-8601 UTC timestamp."""
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")


def validate(record: dict) -> None:
    """Check a record against the JSON Schema and the semantic rules; raise on failure."""
    VALIDATOR.validate(record)
    if not math.isfinite(record["availability"]["hours"]):
        raise ValueError("effort must be finite")
    if record["kind"] == "need" and record["availability"]["hours"] <= 0:
        raise ValueError("an actionable need requires positive effort")
    times = [record[k] for k in ("created_at", "valid_from", "valid_until", "fresh_until")]
    times += [record["availability"][k] for k in ("from", "until")]
    for t in times:
        epoch(t)
    if epoch(record["valid_from"]) >= epoch(record["valid_until"]):
        raise ValueError("empty validity interval")
    if epoch(record["availability"]["from"]) >= epoch(record["availability"]["until"]):
        raise ValueError("empty availability interval")
    if record["kind"] == "need" and (not record["requires"] or record["provides"]):
        raise ValueError("need requires a capability and cannot offer one")
    if record["kind"] == "offer" and (not record["provides"] or record["requires"]):
        raise ValueError("offer provides a capability and cannot request one")
    # Atomic requests in v1 avoid silently satisfying one of several requirements.
    if len(record["requires"]) > 1:
        raise ValueError("v1 supports one requirement per atomic contribution")


@dataclass(frozen=True)
class Actor:
    """Trusted embedding boundary. Adapters must authenticate this object."""

    subject: str
    container: str


@dataclass(frozen=True)
class Scope:
    agent: str
    container: str
    purpose: str = "discovery"


@dataclass(frozen=True)
class Bridge:
    capability: str
    requirement: str
    evidence_id: str
    explanation: str
    limitation: str
    # Reviewed configuration, not inferred from contribution prose.
    source_domain: str
    target_domain: str
