"""First acceptance test: genuinely separate processes and 21-day timestamps."""
import json
import sqlite3
import subprocess
import sys

from conftest import ROOT


def test_00_three_week_cross_container_restart(tmp_path, sprint):
    db = tmp_path / 'single-authority.sqlite'
    fixture = ROOT / 'fixtures/sprint_reconstruction.json'
    def run(phase):
        proc = subprocess.run([sys.executable, '-m', 'utsa_core.demo', phase,
                               '--db', str(db), '--fixture', str(fixture)],
                              cwd=ROOT, check=True, capture_output=True, text=True, timeout=30)
        return json.loads(proc.stdout)
    first = run('sprint-old')  # This process terminates before the next one begins.
    assert first['matches'] == []
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT count(*) FROM records').fetchone()[0] == 1
    later = run('sprint-new')
    matches = [r for r in later if r['type']=='GenuineOpportunity']
    assert len(matches) == 1
    assert matches[0]['age_gap_seconds'] == 21 * 24 * 3600
    assert matches[0]['supports'] == [{'id':'sprint-b:need','revision':1},{'id':'sprint-a:offer','revision':1}]
    assert sprint['offer']['origin']['container'] != sprint['need']['origin']['container']
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT count(*) FROM records').fetchone()[0] == 2
        assert conn.execute('SELECT count(*) FROM relationships').fetchone()[0] == 3
    assert list(tmp_path.glob('*.sqlite')) == [db]


def test_without_old_record_no_invented_match(tmp_path):
    proc = subprocess.run([sys.executable, '-m', 'utsa_core.demo', 'sprint-new',
                           '--db', str(tmp_path/'empty.sqlite'), '--fixture', str(ROOT/'fixtures/sprint_reconstruction.json')],
                          cwd=ROOT, check=True, capture_output=True, text=True, timeout=30)
    assert json.loads(proc.stdout) == []
