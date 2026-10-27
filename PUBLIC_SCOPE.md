# Public scope and data availability

Repository: https://github.com/Javad-Alizargar/limitaware

This repository contains the installable LimitAware 0.1.4 software, tests, policies,
documentation, website source, examples and public-safe evaluation metadata.

It does **not** contain:

* raw Water Quality Portal result exports;
* held-out or external-evaluation CSVs;
* row-level canonical/prepared data whose redistribution is unresolved;
* manuscript administration, private review packets or infrastructure credentials.

## A. Software-only path (promised and tested here)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install .
python evaluation/verify_software.py
```

`evaluation/verify_software.py` checks the installed package, policies, fixtures and
software tests. It exits 0 without study data.

## B. Full study path (requires a separate authorized bundle)

```bash
python evaluation/run_expanded_study.py --stage verify
python evaluation/run_expanded_study.py --stage all --workdir /tmp/limitaware_replay
```

Without the five held-out WQP CSVs and archived reference outputs, `verify` exits 2
and prints the missing-bundle inventory. The study bundle is held privately because
redistribution permission for the source CSVs and derived row-level files is not
confirmed. Retrieval URLs, selection records and SHA-256 digests are included.

The live demonstration at https://wqp.statwhy.com is a living interface, not an
immutable evaluated archive. No DOI is asserted.
