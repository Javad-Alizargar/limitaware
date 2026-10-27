# limitaware 0.1.4

Provenance-preserving preparation of Water Quality Portal (WQP) result exports.
It does **not** estimate anything: it turns a raw export into a canonical table,
an analysis input with explicit censoring, and an audit record, so that an
established estimator (e.g. NADA) can be run reproducibly.

## What it is for

A WQP export mixes detected and non-detected results, several limit types,
fractions, units, methods and QC activities in one table. Deciding which rows mean
what is a *semantic* decision. `limitaware` records that decision explicitly and
never drops a row silently.

## Install

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install .
limitaware --version
```

Python ≥ 3.10, standard library only. R/NADA is an optional validation dependency;
it is not required to run the tool.

## Use

```bash
limitaware inspect   export.csv
limitaware validate  export.csv --policy policies/reporting_total.json
limitaware transform export.csv --policy policies/reporting_total.json --out out/
limitaware compare-policies export.csv \
    --policies policies/reporting_total.json,policies/anylimit_total.json --out cmp/
```

Outputs per transform:

| file | content |
| --- | --- |
| `canonical.csv` | every source row with raw and parsed fields and a status |
| `analysis.csv` | `obs`, `censored`, result id, source row, analyte, fraction, method, limit role, unit |
| `audit.json` | input SHA-256, contract, policy, counts, rules |
| `methods_note.md` | generated description of what was actually done |

## Contract (short)

Supported input: **WQP `Result/search` CSV** (`mimeType=csv&zip=no`), with the
detection/quantitation limit **inline**. A separate limits export is optional and
cannot be joined unambiguously, because the Result CSV has no `ResultIdentifier`.
See `docs/INPUT_CONTRACT.md`.

## Policies

A policy decides which limit roles may define censoring, which fractions and
methods are admissible, unit conversion, below-LOQ handling and duplicates. See
`docs/POLICIES.md`. Policies are not rankings: a stricter policy is not
scientifically superior.

## Verification scopes

**A. Software installation and software-only verification (works from this public
archive).** Install the package, then run:

```bash
pip install .
python evaluation/verify_software.py
```

This runs the package tests, policies and fixtures and exits 0. It does **not**
reproduce the paper's study results and does not need WQP study data.

**B. Full study replay (requires the separate study bundle).** `python
evaluation/run_expanded_study.py --stage verify` checks exact file hashes and exits
2 with a missing-bundle list when the five held-out WQP CSVs and reference outputs are
absent. With the authorized study bundle present, `--stage all --workdir DIR`
replays agreement, policy transitions and downstream summaries. These WQP files are
not included here because redistribution permission is unresolved; retrieval URLs,
selection records and SHA-256 digests are included.

## Data availability

No raw WQP exports are included in this public software archive. The archive contains
software, tests, policies, documentation, example fixtures and public-safe metadata.
The private research bundle contains the study inputs and derived outputs. The living
demo at https://wqp.statwhy.com is not the immutable evaluated archive.

## Limitations

One input profile; no estimates; no GUI; no multiple-limit linkage; no inference
of missing metadata. Rows that cannot be interpreted are reported, not repaired.
