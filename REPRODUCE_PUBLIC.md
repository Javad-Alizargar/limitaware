# Reproducing the public LimitAware package

There are two scopes. Do not confuse them.

## A. Software-only (promised by the public package)
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install .
python evaluation/verify_software.py
```
Checks the installed version, shipped policies, the 11 hand-labelled fixtures and the
62 package tests. It does **not** reproduce the paper's study results and does not
need the held-out data.

## B. Full study replay (requires the study bundle)
`evaluation/run_expanded_study.py --stage all` needs the five held-out WQP CSVs, the
selection records, the policy variants, the matched baseline script, the canonical
reference tables and R/NADA. The exact list and SHA-256 digests are in
`evaluation/STUDY_REPRODUCTION_REQUIREMENTS.json`. These files are not in the public
package because redistribution permission for the held-out CSVs is not confirmed.

When a complete study bundle is present, run:
```bash
python evaluation/run_expanded_study.py --stage verify
python evaluation/run_expanded_study.py --stage all --workdir /tmp/la_replay
```
`verify` reports every missing required file and exits non-zero rather than claiming a
partial replay. The full review archive contains this bundle.
