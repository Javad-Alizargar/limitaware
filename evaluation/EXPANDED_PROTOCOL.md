# Expanded evaluation protocol — LimitAware 0.1.3

Frozen: 2026-10-26, before any expanded download or outcome inspection. Any
deviation is logged in `evaluation/EXPANDED_DEVIATIONS.md`.

## 1. Software and policies under test

| item | value |
| --- | --- |
| Package | LimitAware 0.1.3 (released source tree) |
| `canonical.py` SHA-256 (16) | `39dab1988f13738e` |
| `policies.py` SHA-256 (16) | (recorded in `evaluation/results/expanded_manifest.json` at run time) |
| `reporting_total.json` SHA-256 (16) | `50674504d58d53af` |
| `reporting_dissolved.json` SHA-256 (16) | `ab5ba26ce362f9f7` |
| Python | CPython 3.14.7, macOS 14.1 (Apple M1) |

No source code changes are allowed during the held-out phase. Policy files may be
added only to isolate one documented setting (see §6); the shipped policies and
their conversion tables are frozen. If a defect is found, it is recorded, fixed in a
new version, and the affected analyses are re-run and reported as post-defect.

## 2. Evidence partitions

* **Development (not external validation):** Iowa Atrazine 2019–2021 (933 rows),
  New York Metolachlor 2021 (140), Ohio Prometon 2021 (27).
* **Held-out:** exports selected by §3 after this protocol is hashed.
* **Contract cases:** existing 21 labels, 10 hand-labelled fixture cases, and a
  held-out label sample (§7).
* **Synthetic:** fixtures and the performance replication file only.

## 3. Held-out selection rule

Source: Water Quality Portal `GET /data/Result/search`, `mimeType=csv&zip=no`,
default profile, calendar year 2022, one state and one analyte per export.

Candidate list, fixed in this order (state FIPS, analyte):

1. US:17 Illinois — Atrazine
2. US:18 Indiana — Metolachlor
3. US:26 Michigan — Simazine
4. US:27 Minnesota — 2,4-D
5. US:29 Missouri — Atrazine
6. US:55 Wisconsin — Metolachlor
7. US:21 Kentucky — Chlorpyrifos
8. US:22 Louisiana — Atrazine
9. US:23 Maine — Simazine
10. US:24 Maryland — Metolachlor
11. US:25 Massachusetts — 2,4-D
12. US:28 Mississippi — Atrazine

Rule: take candidates in list order and keep the first **six** that satisfy all of:

* HTTP 200 and a CSV with the 12 required columns;
* 50–5,000 data rows;
* file size ≤ 5 MB;
* fewer than 10% of `(OrganizationIdentifier, ActivityIdentifier)` pairs overlap any
  development export (activity-level overlap check);
* the modal `ResultSampleFractionText` is `Total` or `Dissolved`.

Every attempt, failure, row count, size and digest is recorded, including failures
and skipped candidates. If fewer than six qualify, the study proceeds with those
that do and the shortfall is reported. The download date is recorded; the file is
stored unchanged in `evaluation/expanded/data/` with a SHA-256 digest.

**Policy choice rule.** The policy is selected by the modal fraction: `Total` →
`reporting_total.json`; `Dissolved` → `reporting_dissolved.json`. Units are not
extended after inspection. Rows with units outside the declared conversions are
reported as `unsupported_unit`; if more than 10% of rows in an export are affected,
the export remains in the applicability results and the limitation is recorded.

## 4. Endpoints and denominators

| id | endpoint | definition | denominator |
| --- | --- | --- | --- |
| H1 | profile validity | all 12 required columns present; CSV parses; rows counted | one per export |
| H2 | interpretable coverage | rows whose status is a documented decision (eligible or an `excluded_*`/`duplicate_identical` decision), excluding refusal statuses (ambiguous, conflicting, unsupported, non-finite, missing_limit) | all data rows |
| H3 | eligible fraction | `eligible` rows under the selected policy | all data rows |
| H4 | refusal fraction and reasons | refusal rows by status | all data rows |
| H5 | matched-baseline agreement | eligible-set identity, maximum absolute observation difference, censoring mismatches, group-key equality, status disagreements | rows / eligible rows |
| H6 | policy transitions | paired row status under P0 vs Pk | all data rows |
| H7 | downstream summaries | NADA estimates by homogeneous group, policy P0 vs Pk | groups with estimable fits |
| H8 | runtime | CLI wall time and peak memory, repeated runs | 5 repetitions per workload |
| H9 | traceability/reproducibility | every eligible row has source row and input digest; rerun canonical SHA equal; manifest reconciles | outputs |

H2–H4 are descriptive. H5 is a deterministic agreement check. H6 and H7 are paired
within export and group. H8 is a benchmark, not a usability measure.

## 5. Matched baseline

The independent baseline is `evaluation/scripts/baseline_prepare.py` with
`evaluation/configs/baseline_total.json` or `baseline_dissolved.json`, frozen before
held-out runs. It shares the written specification, not code, with LimitAware. It was
written during the earlier evaluation with AI assistance; this is disclosed.

For each held-out export the baseline configuration is matched to the selected
policy: fraction, limit role, unit conversions, QC, below-LOQ, estimated results and
duplicate handling. Agreements are computed on `(OrganizationIdentifier,
ActivityIdentifier, source row)` because `result_uid` is implementation-specific.

Status disagreements are classified:

* **precedence** — both tools exclude the row, and the earlier rule in LimitAware's
  documented order is also triggered (its flag is present);
* **substantive** — otherwise (admission difference, different refusal reason, or a
  rule trigger not present).

## 6. Policy-consequence experiment

Six policy variants are applied to the development Iowa export and to every held-out
export whose fraction matches:

| id | setting changed relative to P0 | policy |
| --- | --- | --- |
| P0 | none (reference) | `reporting_total` / `reporting_dissolved` |
| P1 | limit roles only | all four roles admissible |
| P2 | below-LOQ handling only | `keep_as_detected` |
| P3 | estimated results only | `keep_as_detected` |
| P4 | fraction only | Total and Dissolved both admissible |
| P5 | duplicate handling only | `drop_identical` |

Each variant changes exactly one setting. Variants are not interpreted as a single
multi-setting contrast. Row-level transitions are computed by stable source identity
and reported with reasons (status under each policy). Exports with no duplicates may
show zero for P5; that is reported, not hidden.

## 7. Reference labels and uncertainty

Existing 21 Iowa labels are retained. A held-out label sample is drawn as the first
eight rows per export after sorting by source row and stratifying by status class
(eligible, documented exclusion, refusal), with at least two refusal rows per export
where available. Expected interpretations are written from raw fields and the WQP/WQX
documentation, with a supporting passage or an explicit "insufficient" note.

Certainty classes: **definite** (rule and field semantics unambiguous), **probable**
(documentation indirect), **insufficient** (no authoritative meaning). All labels are
AI-produced; this is not human expert validation. Agreement is reported on definite
cases; probable and insufficient cases are reported separately and are not counted as
correct.

## 8. Statistical analysis

* Deterministic counts: no confidence intervals and no p-values.
* Within-export proportions: Wilson 95% intervals, reported descriptively. Records
  within an export are clustered within organisations/activities; intervals are not
  presented as population uncertainty.
* Across exports: report the range and the distribution of export-level proportions;
  do not pool records as independent.
* Paired comparisons: same rows or same groups under two policies; report counts and
  differences.
* Downstream: NADA `cenfit` (Kaplan–Meier) for left-censored groups with at least
  8 detected values and at least 2 distinct limit values. If a fit is non-identifiable
  or all observations are censored, report the failure and no estimate. ROS is not
  forced. Median and mean with the software's confidence output are recorded.
* Performance: median and range of five runs; peak resident memory from
  `/usr/bin/time -l` where available. Scope stated with the results.
* Multiplicity: no confirmatory hypothesis tests; all comparisons are descriptive or
  deterministic. No p-values are added.

## 9. Deviations, missing data, and stop rules

* A failed download is recorded and the next candidate used; it is never replaced by
  a hand-picked export.
* If fewer than four exports qualify, the study reports the shortfall.
* If a unit, fraction or limit type is outside the supported contract, it is reported
  as unsupported; the policy is not edited post hoc.
* Software defects found during held-out evaluation are documented, fixed in a new
  version, and the affected results are reported as post-defect and separately from
  the frozen held-out run.
* No public release, push or submission is performed.

## 10. Hash

The protocol file is hashed at freeze time and recorded in
`evaluation/EXPANDED_PROTOCOL.sha256`; the hash, software hashes and download date
are written to `evaluation/results/expanded_manifest.json` before results are read.
