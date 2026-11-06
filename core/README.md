# Utsa portable matching and connection core

Executable reference implementation, 4 November 2026. The matching rules run in
MeTTa. Python validates the shared schema, applies access policy, persists state,
and passes an authorized projection to the interpreter. No Discord, Telegram,
Omega, Hives, LLM, API credentials, embedding service, or network call is required
to run the examples after installing the dependencies.

This increment proves two behaviors before any live platform integration:

1. An offer is stored in process one. That process exits. A fresh process accepts
   a need from a different logical source container exactly 21 days later, retrieves
   the permitted offer from the same durable store, and explains the match.
2. A community sensor-data request discovers a useful capability in neuroscience.
   The output separates shared interest, complementary capability, and an
   actionable opportunity candidate, with source revisions and a bounded mapping.

The first example reconstructs the **behavior** of BGI Sprint I using invented
records and an injected clock. It does not replay the original June recording,
run Docker containers, wait three real weeks, or claim the Sprint build used this
code. The curated history establishes the earlier demonstration; its exact seed,
revision, and transcript have not been supplied. See [evidence](docs/evidence.md).

## Run

From this `core` directory, with Python 3.11 or later:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -c requirements-lock.txt -e '.[test]'
.venv/bin/python -m pytest -q
```

The default runner uses Hyperon 0.2.10 as the MeTTa reference interpreter. To
execute the same code on PeTTa, use the verified checkout revision
`ee5cacb6a6ecdd554a1c773aaf47e9a0f8a5af0f` with SWI-Prolog 9.3.9, Janus and PCRE:

```sh
export UTSA_PETTA_RUNNER=/absolute/path/to/PeTTa/run.sh
.venv/bin/python -m pytest -q
```

`swipl` must be on `PATH`, and its Janus extension must be able to load the Python
shared library. On a custom Python build that may require its `lib` directory on
`LD_LIBRARY_PATH`. The adapter rejects startup errors even if PeTTa exits zero.
The fixture CLI also honors `UTSA_PETTA_RUNNER`. No Omega process is needed.

Run the regression in two separate invocations, against a new database path:

```sh
.venv/bin/python -m utsa_core.demo sprint-old --db sprint.sqlite --fixture fixtures/sprint_reconstruction.json
.venv/bin/python -m utsa_core.demo sprint-new --db sprint.sqlite --fixture fixtures/sprint_reconstruction.json
.venv/bin/python -m utsa_core.demo cross-domain --db discovery.sqlite --fixture fixtures/cross_domain.json
```

The two example databases are independent test worlds. A running Utsa instance
receives exactly **one** `MemoryPort`; it does not mirror records into a second
authority. Do not run an earlier phase against a later-phase database: the
operational clock deliberately rejects time going backwards.

## What the categories mean

| Result | Evidence required | What it does not establish |
| --- | --- | --- |
| `SharedInterest` | Both permitted records explicitly name a topic | Ability, availability, or a collaboration opportunity |
| `ComplementaryCapability` | Confirmed offered capability, stated requirement, and a direct or explicitly configured domain mapping | Compatible availability, capacity, conditions, or consent |
| `GenuineOpportunity` | Capability fit plus a concrete task, compatible conditions, sufficient capacity, and remaining overlapping confirmed windows | Acceptance, contact disclosure, introduction delivery, or completed work |

These are separate claims. A capability fit need not share an interest. Related
terms are not chained into a match. The domain bridge in the example is a
manually specified test hypothesis, not automatic research understanding or an
independently certified skill. It supports reviewing missing samples and artifacts,
not deciding whether water is safe.

## Contents

- [Contribution schema](utsa_core/contribution.schema.json): versioned, portable records.
- [MeTTa rules](utsa_core/rules.metta): the actual inference and connection-readiness rules.
- [Architecture and policy](docs/architecture.md): ownership, temporal semantics, trust boundary.
- [Integration contract](docs/integration.md): verified Omega surfaces and remaining Hives dependencies.
- [Evidence and limitations](docs/evidence.md): original sources, current test scope, unresolved conflicts.
- `tests/`: assertions covering positive behavior and refusal paths.

[Validation report](VALIDATION.md) records the actual runs and remaining limits.
The [5 November review notes](REVIEW_NOTES.md) describe the imported source,
current Telegram status, and consent and matching limits that a host adapter must preserve.

The older root-level prompt, knowledge base, and Telegram fixtures are preserved.
This is a separate implementation increment, not a change to the deployed bot.
