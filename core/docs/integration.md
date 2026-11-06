# Integration contract and source verification

No live adapter has been enabled. The portable core is usable now through its
Python API, fixture CLI, and MeTTa runtime boundary. This document separates
verified source interfaces from contracts still needed for deployment.

## Verified Omega source

Inspected public repository revision:
`singnet/Omega@b94f7bf44e10852e491967191f1c68643dc9ca90`.
This identifies the inspected source; the deployed Hives version is unconfirmed.

| Surface | Source-confirmed interface | Utsa use and boundary |
| --- | --- | --- |
| Plugin loading | `loadOmegaPlugin`; configured `name`, `loader`, optional `location` | Register a callable Utsa wrapper after runtime and host-memory binding are verified. |
| MeTTa skill registration | `(add-skill $function $description $arguments)` | Expose discovery through a narrow function; derive scope from authenticated host context. |
| Loop callback | `(add-heartbeat-listener $handle $callback)` | Possible bounded scheduling hook; cadence and user-follow-up policy need separate verification. |
| Long-term memory | `(remember $str)`, `(query $str)`; Python/ChromaDB bridge | Semantic recall exists. These signatures do not establish Utsa's revision, transaction, access-control, or deletion contract. |
| Message channel | `send` targets the active channel | This alone does not verify recipient-specific private introductions. |

Source links at that revision:

- [Plugin API](https://github.com/singnet/Omega/blob/b94f7bf44e10852e491967191f1c68643dc9ca90/docs/reference-plugin-api.md)
- [Skill implementation](https://github.com/singnet/Omega/blob/b94f7bf44e10852e491967191f1c68643dc9ca90/src/skills.metta)
- [Memory implementation](https://github.com/singnet/Omega/blob/b94f7bf44e10852e491967191f1c68643dc9ca90/src/memory.metta)
- [Communication reference](https://github.com/singnet/Omega/blob/b94f7bf44e10852e491967191f1c68643dc9ca90/docs/reference-skills-communication.md)

Source discrepancy to resolve: the memory reference describes fresh reasoning
spaces, while current `src/skills.metta` evaluates the supplied expression and
its catalogue mentions `&persistent`. Neither observation establishes controlled
restart durability or cross-workspace permissions for Utsa. Test the selected
host revision before assigning authority to any named space.

## Hives interface status

The proposed integration needs authenticated identity, permitted data access,
and recipient-specific private interaction. No exact Hives repository revision, executable
matching-hook signature, scoped-memory API, or authenticated test instance was
available for this implementation. No Hives API path or SDK has been invented.

## Minimum host adapter

Map these requirements to the actual host interfaces, then run the same contract
suite with the host adapter substituted for `SQLiteMemory`:

1. **Identity and ingress:** derive `Actor` and `Scope` from host authentication;
   verify accountable-owner delegation for projects and agents; map stable source
   event IDs into namespaced contribution IDs. Never accept owner, grants, or
   workspace authority from free text or model-generated tool arguments.
2. **One memory authority:** implement the `MemoryPort` read/transaction/relationship/
   decision operations and schema-validated ingestion/policy operations against the
   designated host service. Keep source revisions and grants together. Search
   indexes may be derived; their results are candidates, not authoritative records.
3. **Discovery:** normalize a permitted contribution; invoke `Utsa.discover` for
   its ID under the host-derived purpose and destination. Never send raw internal
   discovery results to a user or broad LLM context. Use recipient-specific preview.
4. **Consent and disclosure:** display each owner's permitted summary privately;
   bind replies to the exact suggestion/revisions. Before resolving or sharing
   contact details, require explicit field-level disclosure grants and recheck
   policy at delivery. The current intent intentionally requests this host work.
5. **Delivery:** use an actual recipient-addressed private interface with an
   idempotency key and truthful receipt. Failure remains pending or failed. Do not
   fall back to a public channel. Acceptance is not delivery or completed work.
6. **Temporal updates:** corrections, withdrawal, freshness, pause, grant revocation,
   and deletion must invalidate derived outputs. A cached intent cannot bypass
   these changes. Preserve atomicity or equivalent version-checked writes.

Reuse existing host identity, persistence, scheduling, private UI, and delivery
where their behavior passes those tests. Do not build an independent replacement
for an adequate host component. Do not copy the same source contribution into
SQLite, ChromaDB and another graph as competing authorities.

If changing authority, use a deliberate migration: pause writes; export a permitted
revision/policy snapshot; import into the chosen provider; verify IDs, revisions,
grants and restart behavior; switch the one provider; disable old writes. If it
fails, remain on the prior authority. This procedure is a plan, not implemented
cross-system synchronization.

## Evidence needed before a live pilot

| Required evidence | Owner to identify |
| --- | --- |
| Exact Hives/Omega/PeTTa revisions and smallest working integration example | Host engineer |
| Chosen authoritative store and supported read/write/revoke/delete/transaction methods | Host engineer |
| Authenticated subject, container, and delegated-owner mapping | Host engineer |
| Recipient-specific private preview, acceptance, disclosure and receipt interfaces | Host engineer |
| Restart test and cross-container denial/revocation tests against that store | Integration tester |
| Approved real contribution pair and audience, plus domain-bridge review if used | Operator and contribution owners |

Reproduce the independent regression suite before integration. Hives remains
the intended first live integration; Telegram is a separate deployment track.
No launch commitment, assigned engineer, live delivery, complete attestation,
or reputation behavior is asserted here.
