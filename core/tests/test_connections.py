import copy
import json

import pytest

from conftest import allow_previews, opportunities
from utsa_core.demo import seed
from utsa_core.model import Actor, Scope, epoch
from utsa_core.engine import Utsa
from utsa_core.memory import SQLiteMemory


def test_discovery_permission_does_not_allow_preview(system):
    engine,store,scope,now,f=system
    key=opportunities(engine,f,scope,now)[0]['id']
    with pytest.raises(PermissionError):engine.preview(key,Actor('person-a','pilot'),scope,now)


def test_preview_is_minimized_and_recipient_scoped(system):
    engine,store,scope,now,f=system
    key=opportunities(engine,f,scope,now)[0]['id']
    allow_previews(store,f,scope,now)
    preview=engine.preview(key,Actor('person-a','pilot'),scope,now)
    assert preview['summaries']==[f['need']['permitted_summary'],f['offer']['permitted_summary']]
    assert 'person-b' not in json.dumps(preview)
    assert 'source_ref' not in json.dumps(preview)
    assert 'supports' not in preview
    for actor in (Actor('intruder','pilot'),Actor('person-a','wrong')):
        with pytest.raises(PermissionError):engine.preview(key,actor,scope,now)


def test_bilateral_revision_scoped_intent_and_reversal(system):
    engine,store,scope,now,f=system
    key=opportunities(engine,f,scope,now)[0]['id']
    allow_previews(store,f,scope,now)
    assert engine.connection_intent(key,scope,now) is None
    engine.decide(key,Actor('person-a','pilot'),scope,True,now)
    assert engine.connection_intent(key,scope,now) is None
    engine.decide(key,Actor('person-b','pilot'),scope,True,now)
    intent=engine.connection_intent(key,scope,now)
    assert intent['delivered'] is False
    assert intent['state']=='ready-for-host-authorization'
    assert engine.connection_intent(key,scope,now)==intent
    engine.decide(key,Actor('person-b','pilot'),scope,False,now)
    assert engine.connection_intent(key,scope,now) is None


@pytest.mark.parametrize('permission',['discover','preview'])
def test_revocation_after_both_accept_blocks_action(system,permission):
    engine,store,scope,now,f=system
    key=opportunities(engine,f,scope,now)[0]['id']
    allow_previews(store,f,scope,now)
    for owner in ('person-a','person-b'):engine.decide(key,Actor(owner,'pilot'),scope,True,now)
    r=f['offer']
    principal='utsa' if permission=='discover' else 'person-a'
    store.grant(Actor('person-b','sprint-a'),r['id'],1,principal,'pilot','discovery',permission,False,epoch(r['valid_until']),now)
    if permission=='discover':
        with pytest.raises(PermissionError):engine.connection_intent(key,scope,now)
    else:
        assert engine.connection_intent(key,scope,now) is None


def test_intruder_cannot_accept(system):
    engine,store,scope,now,f=system
    key=opportunities(engine,f,scope,now)[0]['id']
    allow_previews(store,f,scope,now)
    with pytest.raises(PermissionError):engine.decide(key,Actor('intruder','pilot'),scope,True,now)


def test_unknown_relationship_does_not_expose_existence(system):
    engine,store,scope,now,f=system
    with pytest.raises(PermissionError,match='relationship not available'):
        engine.preview('unknown',Actor('intruder','pilot'),scope,now)


def test_acceptance_and_permissions_survive_reopening(system):
    engine,store,scope,now,f=system
    key=opportunities(engine,f,scope,now)[0]['id']
    allow_previews(store,f,scope,now)
    for owner in ('person-a','person-b'):
        engine.decide(key,Actor(owner,'pilot'),scope,True,now)
    reopened=SQLiteMemory(store.authority_id.removeprefix('sqlite:'))
    try:
        intent=Utsa(reopened).connection_intent(key,scope,now)
        assert intent['state']=='ready-for-host-authorization'
        assert intent['delivered'] is False
    finally:
        reopened.close()


def test_self_match_and_utsa_candidate_excluded(system):
    engine,store,scope,now,f=system
    store.delete(Actor('person-b','sprint-a'),f['offer']['id'],now)
    r=copy.deepcopy(f['offer']);r['owner']='person-a';r['entity']['id']='person-a'
    seed(store,r,'pilot',now)
    assert engine.discover(f['need']['id'],scope,now)==[]
    store.delete(Actor('person-a','sprint-a'),r['id'],now)
    r['owner']='utsa';r['entity']={'id':'utsa','type':'agent'}
    seed(store,r,'pilot',now)
    assert engine.discover(f['need']['id'],scope,now)==[]
