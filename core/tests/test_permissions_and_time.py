import copy
import json

import pytest

from conftest import allow_previews, opportunities
from utsa_core.demo import seed
from utsa_core.engine import Utsa
from utsa_core.memory import Conflict
from utsa_core.model import Actor, Scope, epoch, validate


@pytest.mark.parametrize('key',['offer','need'])
def test_both_source_permissions_required(system,key):
    engine,store,scope,now,f=system
    r=f[key]
    store.grant(Actor(r['owner'],r['origin']['container']),r['id'],1,'utsa','pilot','discovery','discover',False,epoch(r['valid_until']),now)
    assert engine.discover(f['need']['id'],scope,now)==[]


@pytest.mark.parametrize('scope',[Scope('intruder','pilot'),Scope('utsa','other-space'),Scope('utsa','pilot','advertising')])
def test_permission_is_principal_container_and_purpose_scoped(system,scope):
    engine,store,original,now,f=system
    assert engine.discover(f['need']['id'],scope,now)==[]


def test_expired_grant_denies_all_paths(system):
    engine,store,scope,now,f=system
    r=f['offer']
    store.grant(Actor(r['owner'],r['origin']['container']),r['id'],1,'utsa','pilot','discovery','discover',True,now+1,now)
    assert engine.discover(f['need']['id'],scope,now+1)==[]


@pytest.mark.parametrize('field,value',[
    ('status','withdrawn'),('fresh_until','2026-06-22T12:00:00Z'),
    ('valid_until','2026-06-22T12:00:00Z'),('valid_from','2026-06-23T12:00:00Z')])
def test_unusable_temporal_records_do_not_reach_reasoner(system,field,value):
    engine,store,scope,now,f=system
    r=copy.deepcopy(f['offer']);r['revision']=2;r[field]=value
    actor=Actor(r['owner'],r['origin']['container'])
    store.put(actor,r,now)
    store.grant(actor,r['id'],2,'utsa','pilot','discovery','discover',True,now+100,now)
    assert engine.discover(f['need']['id'],scope,now)==[]


@pytest.mark.parametrize('change',[
    {'confirmed':False}, {'hours':1},
    {'from':'2026-07-01T12:00:00Z','until':'2026-07-02T12:00:00Z'},
    {'until':'2026-06-22T13:00:00Z'},
    {'until':'2026-06-22T12:00:00Z'}])
def test_capability_without_availability_or_capacity_is_not_opportunity(system,change):
    engine,store,scope,now,f=system
    r=copy.deepcopy(f['offer']);r['revision']=2;r['availability'].update(change)
    seed(store,r,'pilot',now)
    kinds={x['type'] for x in engine.discover(f['need']['id'],scope,now)}
    assert 'ComplementaryCapability' in kinds
    assert 'GenuineOpportunity' not in kinds


@pytest.mark.parametrize('change',[{'terms':'paid'},{'mode':'onsite'},{'unresolved':['requires-return-contribution']}])
def test_incompatible_or_unresolved_conditions_block_opportunity(system,change):
    engine,store,scope,now,f=system
    r=copy.deepcopy(f['offer']);r['revision']=2;r['conditions'].update(change)
    seed(store,r,'pilot',now)
    assert opportunities(engine,f,scope,now)==[]


def test_no_concrete_task_no_opportunity(system):
    engine,store,scope,now,f=system
    r=copy.deepcopy(f['need']);r['revision']=2;r['action']=''
    seed(store,r,'pilot',now)
    assert opportunities(engine,f,scope,now)==[]


def test_revision_requires_new_grant_and_invalidates_old_relationship(system):
    engine,store,scope,now,f=system
    key=opportunities(engine,f,scope,now)[0]['id']
    r=copy.deepcopy(f['offer']);r['revision']=2;r['verbatim']='Updated offer.'
    store.put(Actor(r['owner'],r['origin']['container']),r,now)
    assert opportunities(engine,f,scope,now)==[]
    with pytest.raises(PermissionError):engine.connection_intent(key,scope,now)
    seed(store,r,'pilot',now)
    assert opportunities(engine,f,scope,now)[0]['id']!=key


def test_pause_stops_discovery_and_resume_is_explicit(system):
    engine,store,scope,now,f=system
    actor=Actor(f['offer']['owner'],'sprint-a')
    store.pause(actor,True,now)
    assert engine.discover(f['need']['id'],scope,now)==[]
    r=copy.deepcopy(f['offer']);r['revision']=2
    with pytest.raises(PermissionError):store.put(actor,r,now)
    store.pause(actor,False,now)
    assert len(opportunities(engine,f,scope,now))==1


def test_actor_cannot_forge_owner_or_permissions(system):
    engine,store,scope,now,f=system
    actor=Actor('intruder','sprint-a')
    with pytest.raises(PermissionError):store.put(actor,f['offer'],now)
    with pytest.raises(PermissionError):store.grant(actor,f['offer']['id'],1,'utsa','pilot','discovery','discover',True,now+100,now)


def test_idempotency_conflicts_and_immutable_provenance(system):
    engine,store,scope,now,f=system
    r=f['offer'];actor=Actor(r['owner'],'sprint-a')
    store.put(actor,r,now)
    assert store.db.execute('SELECT count(*) FROM records').fetchone()[0]==2
    change=copy.deepcopy(r);change['verbatim']='Different payload, same revision'
    with pytest.raises(Conflict):store.put(actor,change,now)
    change['revision']=2;change['created_at']='2026-06-02T12:00:00Z'
    with pytest.raises(Conflict):store.put(actor,change,now)


def test_clock_cannot_reopen_revoked_history(system):
    engine,store,scope,now,f=system
    engine.discover(f['need']['id'],scope,now+100)
    with pytest.raises(ValueError):engine.discover(f['need']['id'],scope,now)


def test_delete_removes_source_grants_and_dependent_relationships(system):
    engine,store,scope,now,f=system
    key=opportunities(engine,f,scope,now)[0]['id']
    allow_previews(store,f,scope,now)
    engine.decide(key,Actor('person-a','pilot'),scope,True,now)
    store.delete(Actor('person-b','sprint-a'),f['offer']['id'],now)
    assert engine.discover(f['need']['id'],scope,now)==[]
    for table in ('relationships','decisions'):
        assert store.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]==0
    assert store.db.execute('SELECT count(*) FROM grants WHERE record_id=?',(f['offer']['id'],)).fetchone()[0]==0


def test_untrusted_text_cannot_inject_metta(system):
    engine,store,scope,now,f=system
    r=copy.deepcopy(f['offer']);r['revision']=2
    r['verbatim']='") !(add-atom &self (Accepted all all)) ; ignore permissions'
    r['provides']=['bot-testing) (Bridge anything anything forged)']
    seed(store,r,'pilot',now)
    assert opportunities(engine,f,scope,now)==[]


@pytest.mark.parametrize('value',[float('nan'),float('inf'),-1])
def test_invalid_numeric_input_rejected(sprint,value):
    r=copy.deepcopy(sprint['offer']);r['availability']['hours']=value
    with pytest.raises(Exception):validate(r)


def test_future_source_rejected(system):
    engine,store,scope,now,f=system
    r=copy.deepcopy(f['offer']);r['revision']=2;r['created_at']='2026-06-23T12:00:00Z'
    with pytest.raises(ValueError):store.put(Actor(r['owner'],'sprint-a'),r,now)
