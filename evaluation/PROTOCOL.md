# Evaluation protocol (frozen before execution)

Date: 2026-10-25. Status: **written before any evaluation run**. Any deviation is
recorded in `reports/LIMITAWARE_PUBLICATION_EVIDENCE.md`.

## 1. Software under evaluation

| item | value |
| --- | --- |
| Package | `dist/limitaware-0.1.2.tar.gz` |
| Archive SHA-256 (16) | `c553b010c255c48b` |
| Core module SHA-256 (16) | `d7f738a2485de1a5` (`canonical.py`) |
| Policy module SHA-256 (16) | `06945c7667b7d856` (`policies.py`) |
| Policies | `reporting_total` `c59a28f8d0f6cda2`; `anylimit_total` `631c11e52361a93a`; `reporting_dissolved` `62a2f880e465132d` |
| Development export (Iowa) | `/tmp/wqp_US3A19.csv`, SHA-256 (16) `1a37409f898f3872` |
| Previously inspected export (California) | `333a7449b83936c7` |

Iowa is **development data**. California has already been inspected and is **not**
an unseen validation dataset. All hashes are frozen in
`evaluation/frozen_hashes.json`.

## 2. Supported task and input contract

Task: prepare a Water Quality Portal `Result/search` CSV (default profile,
`mimeType=csv&zip=no`, inline limit) for left-censored analysis under an explicit
policy, producing a canonical table, per-group analysis inputs and an audit record.
The supported contract is documented in `docs/INPUT_CONTRACT.md` of the package.

## 3. Questions and outcomes

| id | question | outcome | denominator |
| --- | --- | --- | --- |
| Q1 | Does the software's interpretation agree with the documented expectation for each assessed record? | agreement count, disagreement list | assessed records with a definite expectation |
| Q2 | Are incorrect admissions and incorrect exclusions avoided? | count of each | assessed records |
| Q3 | Are genuinely ambiguous records retained as unresolved rather than forced into a category? | retained / forced count | records labelled "insufficient documentation" |
| Q4 | Is every analysis row traceable to a source digest, row and decision? | traceability check pass/fail per row | eligible rows |
| Q5 | Are reruns byte-identical and manifest-consistent? | byte comparison, manifest reconciliation | all outputs |
| Q6 | Can the package process two additional exports without code changes, and what configuration is needed? | successful runs, required policy edits, unsupported records | two exports |

## 4. Dataset-selection procedure (fixed before inspection)

**Assessment set (Iowa).** From the frozen development export, select the first
three rows (ascending source row) satisfying each of ten raw-field criteria, giving
up to 30 records: (a) `Not Detected` with a reporting limit; (b) `Not Detected`
with a method detection level; (c) qualifier `J`; (d) qualifier `DL`; (e) blank
result unit; (f) QC activity; (g) `Dissolved` fraction; (h) `Lower Quantitation
Limit`; (i) plain detected value; (j) no limit. Selection uses **source fields
only**, never tool output.

**Additional exports (Q6).** Two queries, fixed before looking at responses:
1. `statecode=US:36` (New York), `characteristicName=Metolachlor`, 2021-01-01 to
   2021-12-31, `mimeType=csv&zip=no`.
2. `statecode=US:39` (Ohio), `characteristicName=Prometon`, 2021-01-01 to
   2021-12-31, `mimeType=csv&zip=no`.

Rationale: two states and two analytes not used in development, same year, one
pesticide analyte each, chosen for variation in source organisation and reporting
conventions. If a response exceeds 6 MB, the window is narrowed to January–June
and this is recorded. No export is replaced because of its content.

## 5. Interpretation-label procedure

Labels are written from official documentation (WQP Web Services Guide; WQX code
documentation where reachable; source-agency conventions only when documented).
For each record the reference table records: source digest and row, relevant raw
fields, expected source meaning, expected eligibility under `reporting_total`,
supporting passage, certainty (`definite` / `probable` / `insufficient`), and open
questions.

Rules:
* Expected labels are **not** derived from LimitAware output.
* Where documentation does not establish a meaning (e.g. the `DL` qualifier if no
  authoritative list is found), the label is `insufficient documentation` and the
  record is counted as "unresolved expected", not as eligible or excluded.
* Source meaning, analyst policy choice and software execution are recorded
  separately.
* One AI produced all labels. This is **not** independent expert validation; the
  limitation is stated in the report.

## 6. Baseline specification

An independent Python preparation script (`evaluation/scripts/baseline_prepare.py`)
written from the same documentation, without importing or copying LimitAware code.
It must implement: column validation, qualifier/condition interpretation, unit
conversion, policy filters (fraction, QC, limit role), grouping by
analyte/fraction/method, per-group CSV output, and an audit record with input hash
and counts. It is allowed to be simpler in presentation; it must not omit ordinary
validation or provenance deliberately.

Both tools receive the same input file, the same policy rules (as a plain JSON
config) and must produce the same intended outputs.

## 7. Ambiguous cases

Records with undocumented qualifiers, unknown limit types, missing units or
conflicting evidence are expected to remain unresolved. For Q1 they are excluded
from the agreement denominator and reported separately in Q3.

## 8. Analysis and reporting

* Counts with explicit denominators; no percentage without the denominator.
* Valid policy differences are separated from interpretation errors.
* Acceptance rates are not treated as quality: more rows accepted or more refusals
  is neither better nor worse by itself.
* NADA agreement (already established) is **not** used as evidence of correct
  interpretation.
* Timing, if measured, uses `perf_counter` on the same machine, same input, three
  runs, median reported, and is labelled as execution time only.
* If the tools perform equivalently on interpretation, that is reported and the
  contribution is re-assessed on other demonstrated capabilities.
