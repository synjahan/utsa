# Portable-core import and integration notes

5 November 2026.

## Source and scope

This directory imports the implementation from `Utsa-portable-core-2026-11-04.zip`
(SHA-256 `26a33e7aab977e5cabc8054a46da024e3dda3bbe25de2f76feee063f62cace54`).
The executable source, schema, synthetic fixtures, tests, and dependency pins
are unchanged. Documentation has been updated for a repository handoff, and
private workspace references and an environment-specific installation log are
excluded. The full independent review remains a separate handoff document.

The prior repository baseline was
`68d55f243eec5df4bb04a6f46a96ef9bcccbefc9`. It contained the Telegram prompt,
knowledge base, synthetic Telegram seed, README, and licence. It did not contain
this executable core. Existing prompt, knowledge base, and seed files are preserved.

## Evidence boundaries

- The archived validation records 46 passing tests on Hyperon 0.2.10 and the
  same 46 on PeTTa revision `ee5cacb6a6ecdd554a1c773aaf47e9a0f8a5af0f`
  with SWI-Prolog 9.3.9. These are local synthetic tests.
- The persistence regression uses separate processes and an injected clock
  advanced by 21 days. It is not evidence of three weeks of live operation,
  deployed Docker containers, or current Telegram/Hives permissions.
- The Telegram operator reports that the bot responds and identifies itself.
  Its complete matching/private introduction loop remains untested, and its
  deployed revision and use of this core are not established.
- Hives integration is not implemented. A host must supply trusted identity,
  one authoritative memory provider, permitted private previews, separate
  participant choices, and authorized delivery with a truthful receipt.

## Behaviors the host must understand

1. **Same-owner exclusion.** The rules exclude distinct entities with the same
   accountable owner. Supporting two agents owned by one team requires an
   explicit relation-specific policy change and tests.
2. **Preview text.** The core returns an authorized `permitted_summary` unchanged.
   The host must ensure pre-acceptance summaries do not reveal identifying
   details. Approval of a summary is not proof that it is anonymous.
3. **Restored permission.** Revoking then restoring access to the same revision
   can reactivate earlier acceptances. Whether revocation requires a new
   acceptance round remains an explicit product decision. Fresh acceptance is
   the independent review's recommendation for the first live pilot.
4. **Candidate capacity.** Capacity is checked per candidate. Multiple candidates
   can reference the same available hours. The core does not reserve capacity,
   book work, or establish that all candidates can proceed together.
5. **Atomic needs.** Python validation allows one required capability per atomic
   need. Adapters must use that validation as well as the JSON Schema.
6. **Delivery boundary.** `Utsa.connection_intent` returns `delivered: false`.
   Both acceptances alone do not send a message, disclose contact fields, or
   prove that work occurred.

## Smallest useful engineering task

Reproduce the local tests, then connect one authenticated host invocation using
synthetic records. Confirm the real host's interfaces before implementing its
adapter. Reuse suitable host capabilities and keep one authoritative store for
contributions, revisions, grants, and decisions. No speculative Hives endpoint,
additional orchestrator, or second authoritative memory store is required.
