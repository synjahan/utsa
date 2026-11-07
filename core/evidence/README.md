# Test evidence and publication normalization

These files record two separate validation dates:

| Files | Run date | Runtime and result |
| --- | --- | --- |
| `hyperon-tests.txt`, `hyperon-tests.xml` | 4 November 2026 | Archived Hyperon run: 46 passed |
| `petta-tests-verified.txt`, `petta-tests-verified.xml` | 4 November 2026 | Archived PeTTa run: 46 passed |
| `github-import-hyperon-tests.txt`, `github-import-hyperon-tests.xml` | 5 November 2026 | Fresh Hyperon run while preparing the GitHub import: 46 passed |

The PeTTa evidence is carried forward from the archived package; PeTTa was not
rerun as part of the 5 November import check. The original `runtime-manifest.json`
and other archived evidence retain their original scope and date.

For public distribution, machine-specific absolute paths to generated XML files
in the text logs were replaced with repository-relative paths beginning with
`core/evidence/`. Container hostnames in JUnit XML were replaced with `redacted`.
Commands, test names, cases, counts, results, timestamps, timings, and all other
test data are unchanged. The raw installation log is not included.

`polish-2026-11-manifest.json`, `polish-2026-11-hyperon-tests.txt` and `.xml` record the 6 November readability polish run against its own source hashes. `runtime-manifest.json` keeps its original 4 November scope, hashes and results.
