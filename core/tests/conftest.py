import json
from pathlib import Path
import pytest

from utsa_core.demo import seed
from utsa_core.engine import Utsa
from utsa_core.memory import SQLiteMemory
from utsa_core.model import Actor, Scope, epoch

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sprint():
    return json.loads((ROOT / 'fixtures/sprint_reconstruction.json').read_text())


@pytest.fixture
def system(tmp_path, sprint):
    store = SQLiteMemory(tmp_path / 'authority.sqlite')
    now = epoch(sprint['new_time'])
    for key in ('offer', 'need'):
        seed(store, sprint[key], 'pilot', now)
    yield Utsa(store), store, Scope('utsa', 'pilot'), now, sprint
    store.close()


def opportunities(engine, fixture, scope, now):
    return [r for r in engine.discover(fixture['need']['id'], scope, now) if r['type']=='GenuineOpportunity']


def allow_previews(store, fixture, scope, now):
    for key in ('offer', 'need'):
        r = fixture[key]
        for person in ('offer', 'need'):
            store.grant(Actor(r['owner'], r['origin']['container']), r['id'], r['revision'],
                        fixture[person]['owner'], scope.container, scope.purpose, 'preview',
                        True, epoch(r['valid_until']), now)
