# Utsa portable core: implementation and validation

**4 November 2026. Implemented locally; 46 tests pass on each of two MeTTa
runtimes. Live Omega/Hives integration is not implemented.**

## Results

| Requirement | Result | Evidence |
| --- | --- | --- |
| Environment-independent core | Implemented without Discord, Telegram, Omega, Hives, an LLM, or platform credentials | Both runtime suites and fixture CLI |
| Shared contribution schema | Implemented as validated JSON Schema 1.0 | `utsa_core/contribution.schema.json` |
| Permissioned temporal relationship memory | Implemented with revision-specific grants, source/event time, validity, freshness, revocation and derived relationships in one authority | Permission, temporal, restart and connection tests |
| Sprint I behavior as first regression | Passed: older offer written by one process; later need from another logical container matched by a fresh process at exactly +21 days | `test_00_three_week_cross_container_restart` |
| Explainable cross-domain discovery | Passed: interest only, capability with unknown availability, and feasible opportunity remain distinct | `test_cross_domain_three_distinct_claims` and sample output |
| MeTTa reasoning on PeTTa | Passed; capability equality, reviewed domain transfer, conditions, capacity, time windows and consent readiness are MeTTa rules | PeTTa suite; same rule file on both runtimes |
| One memory authority | One injected provider; the reference adapter uses one SQLite file per independent test world; projections are disposable | Architecture and first-regression database assertions |
| Verified host integration | Omega source interfaces inspected; Hives contracts unavailable | Integration document; no live adapter enabled |

## Executed validation

| Environment | Verdict | Log |
| --- | --- | --- |
| Python 3.12.14, Hyperon 0.2.10 | 46 passed | [Hyperon log](evidence/hyperon-tests.txt) |
| PeTTa `ee5cacb6a6ecdd554a1c773aaf47e9a0f8a5af0f`, SWI-Prolog 9.3.9 | 46 passed | [PeTTa log](evidence/petta-tests-verified.txt) |
| Both runtimes, both demonstration fixtures | Full result objects match | [Parity check](evidence/runtime-parity.json) |
| Editable Python package installation | Succeeded in the archived validation | [Pinned dependencies](requirements-lock.txt); environment-specific installation log omitted from the public import |

The test runner invokes the real interpreters; there is no mock or Python fallback
matcher. JUnit XML accompanies the logs. PeTTa startup warnings/errors are treated
as failure even when the interpreter exits zero. Its initial local dependency
setup was corrected before the successful runs; no failures were suppressed.

Tests cover both source permissions, wrong principal/container/purpose, expiry,
freshness, withdrawal, revision changes, pause/resume, future timestamps,
incompatible terms, unresolved conditions, insufficient capacity or shared time,
uncertain skills, missing task, self-matches, untrusted text, unauthorized previews,
bilateral choices, revoked consent, deletion of dependent relationships, and
reopening durable state. They do not certify production security or scalability.

## Demonstration outputs

- [Older offer saved](evidence/sprint-old.json)
- [New need matched 21 days later](evidence/sprint-new.json)
- [Cross-domain result set](evidence/cross-domain.json)

In the cross-domain fixture, an ecology reader shares the water-quality interest
but offers no required capability. One neuroscience contributor has a relevant
signal-processing capability with unknown availability. Another has confirmed
availability and capacity to review sensor data for missing samples and artifacts,
so it produces an opportunity candidate. The explicit mapping does not establish
water-safety expertise. Nobody is automatically introduced or assigned work.

## Remaining evidence and decisions

1. **Original Sprint artifacts:** the exact June build, seed and transcript are
   still missing. This is a synthetic behavioral reconstruction with an injected
   21-day clock, not a historical replay or real-time three-week deployment.
2. **Live host revision and contract:** obtain the host's actual Hives/Omega/PeTTa
   revisions and a minimal callable example. The inspected public Omega revision
   is not asserted to be his deployment.
3. **Memory ownership:** select the host's authoritative provider and implement
   the adapter only after its revisions, grants, transactions, deletion and
   restart behavior can satisfy these tests. Do not add a parallel authoritative
   copy of the same contributions.
4. **Identity and connection delivery:** verify authenticated ownership/delegation,
   recipient-specific private UI, explicit contact disclosure, and delivery
   receipts. The core currently returns an undelivered introduction intent.
5. **First live data:** select a permitted real contribution pair. Old Sprint
   records are evidence, not present-day permission or availability.

At the time of the original 4 November validation, no live platform was changed,
no message was sent, and no GitHub push was made.
The root prompt, knowledge base and original Telegram fixture are preserved.
The new `core/` directory and a short README pointer are the repository changes.

## Fresh repository-import check: 5 November 2026

The imported source was installed into a new Python 3.12.14 virtual environment
using `pip install -c requirements-lock.txt -e '.[test]'`. All pinned dependency
versions were available, and the editable installation succeeded.

The unchanged test suite then ran on Hyperon 0.2.10: **46 passed in 11.72 seconds**.
See the [fresh test log](evidence/github-import-hyperon-tests.txt),
[JUnit results](evidence/github-import-hyperon-tests.xml), and
[import manifest](evidence/github-import-manifest.json).

The import retains the original source, schema, fixture, and test bytes.
Documentation changes clarify scope and remove private workspace references.
The archived PeTTa results above were not rerun during this import.
This check did not exercise or change any live Telegram or Hives service.

## Polish, 6 November 2026 (branch `polish-2026-11`)

Readability only; behaviour unchanged. Black formatting (line length 100, double quotes), one-line
docstrings on every public function, `_discover` split into four small methods, `Conflict` renamed
`ConflictError` with the old name kept as an alias, and the duplicated window-overlap test in
`rules.metta` factored into one `windows-overlap` rule. Checks: 46 tests pass on Hyperon 0.2.10;
`smoke_loop_v2.py` exits 0; the demo outputs match the archived evidence in every claim, blocker,
explanation and date. Because `rules.metta` changed, `rule_version` and the derived relation ids
differ from the archived `cross-domain.json` and `sprint-new.json`; that is the versioning working
as designed. The PeTTa run on Omega's pinned `v1.0.4` is still pending.
