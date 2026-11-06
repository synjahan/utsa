import copy
import json
from dataclasses import replace

from conftest import ROOT, opportunities
from utsa_core.demo import seed
from utsa_core.engine import Utsa
from utsa_core.memory import SQLiteMemory
from utsa_core.model import Actor, Bridge, Scope, epoch


def test_cross_domain_three_distinct_claims(tmp_path):
    fixture=json.loads((ROOT/'fixtures/cross_domain.json').read_text())
    memory=SQLiteMemory(tmp_path/'memory.sqlite')
    now=epoch(fixture['time'])
    for r in fixture['contributions']:
        seed(memory,r,'pilot',now)
    bridge=Bridge(**fixture['bridge'])
    engine=Utsa(memory,(bridge,))
    results=engine.discover('water:need',Scope('utsa','pilot'),now)
    def kinds(id):
        return {r['type'] for r in results if any(s['id']==id for s in r['supports'])}
    assert kinds('ecology:interest') == {'SharedInterest'}
    assert kinds('neuro:unavailable') == {'ComplementaryCapability'}
    assert next(r for r in results if r['supports'][1]['id']=='neuro:unavailable')['blockers'] == ['OfferAvailabilityUnknown']
    assert kinds('neuro:offer') == {'ComplementaryCapability','GenuineOpportunity'}
    opportunity=next(r for r in results if r['type']=='GenuineOpportunity')
    assert opportunity['cross_domain'] is True
    assert opportunity['evidence_id']=='bridge:signal-quality-v1'
    assert 'EEG' in opportunity['explanation']
    assert 'water safety' in opportunity['limitation']
    assert all('verbatim' not in r for r in results)
    # Remove the reviewed transfer rule: interests remain, no invented bridge.
    plain=Utsa(memory).discover('water:need',Scope('utsa','pilot'),now)
    assert {r['type'] for r in plain} == {'SharedInterest'}
    # A mapping reviewed for a different domain must not silently transfer.
    wrong=Utsa(memory,(replace(bridge,target_domain='finance'),)).discover('water:need',Scope('utsa','pilot'),now)
    assert {r['type'] for r in wrong} == {'SharedInterest'}
    memory.close()


def test_new_offer_can_trigger_existing_need(system):
    engine,store,scope,now,f=system
    matches=[r for r in engine.discover(f['offer']['id'],scope,now) if r['type']=='GenuineOpportunity']
    assert len(matches)==1


def test_shared_interest_never_sufficient(system):
    engine,store,scope,now,f=system
    r=copy.deepcopy(f['offer']);r['revision']=2;r['provides']=['piano-tuning']
    seed(store,r,'pilot',now)
    results=engine.discover(f['need']['id'],scope,now)
    assert {r['type'] for r in results} == {'SharedInterest'}


def test_unknown_capability_does_not_create_complement(system):
    engine,store,scope,now,f=system
    r=copy.deepcopy(f['offer']);r['revision']=2;r['capability_evidence']='uncertain'
    seed(store,r,'pilot',now)
    assert {r['type'] for r in engine.discover(f['need']['id'],scope,now)} == {'SharedInterest'}


def test_shared_interest_is_symmetric_and_deduplicated(system):
    engine,store,scope,now,f=system
    first={r['id'] for r in engine.discover(f['need']['id'],scope,now) if r['type']=='SharedInterest'}
    second={r['id'] for r in engine.discover(f['offer']['id'],scope,now) if r['type']=='SharedInterest'}
    assert first==second
