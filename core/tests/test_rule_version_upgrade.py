"""A rule-file change starts a new rule version: old suggestions must be rediscovered,
and earlier acceptances never carry across versions (fresh acceptance, decided 6 Nov 2026)."""

import pytest

import utsa_core.engine as engine_module
from conftest import allow_previews, opportunities
from utsa_core.model import Actor


def test_rule_version_change_requires_rediscovery_and_fresh_acceptance(system, monkeypatch):
    engine, store, scope, now, f = system
    old_key = opportunities(engine, f, scope, now)[0]["id"]
    allow_previews(store, f, scope, now)
    engine.decide(old_key, Actor("person-a", "pilot"), scope, True, now)
    engine.decide(old_key, Actor("person-b", "pilot"), scope, True, now)
    assert engine.connection_intent(old_key, scope, now)["delivered"] is False

    # The rules file changes: every relation id derives from the new version.
    monkeypatch.setattr(engine_module, "RULE_VERSION", "0" * 64)

    with pytest.raises(PermissionError):
        engine.connection_intent(old_key, scope, now + 1)
    new_key = opportunities(engine, f, scope, now + 1)[0]["id"]
    assert new_key != old_key
    assert engine.connection_intent(new_key, scope, now + 1) is None  # nobody has accepted yet
    engine.decide(new_key, Actor("person-a", "pilot"), scope, True, now + 1)
    assert engine.connection_intent(new_key, scope, now + 1) is None  # one yes is still not enough
