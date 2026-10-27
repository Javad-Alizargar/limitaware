# Evaluation/reproduction contents

Two scopes are deliberately separate:

## Software-only
`python evaluation/verify_software.py` checks the installed package, policies,
hand-labelled fixtures and the 62 package tests. It requires no study data.

## Full study replay
`python evaluation/run_expanded_study.py --stage all` requires the complete study
bundle: five held-out WQP CSVs, selection records, policy variants, matched baseline,
canonical reference outputs and R/NADA. The exact files and SHA-256 digests are in
`STUDY_REPRODUCTION_REQUIREMENTS.json`. Held-out CSVs are not in the public package
because redistribution permission is not confirmed. Running `--stage verify` without
the bundle prints every missing file and exits non-zero; it does not claim a replay.

The complete bundle is in the full review archive, not the public software archive.
