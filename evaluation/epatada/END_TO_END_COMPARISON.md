# End-to-end EPATADA comparison (post-review)

Date: 2026-10-27. Status: executed.

## Comparator and frozen revisions

* EPATADA 0.0.1, GitHub `USEPA/EPATADA`, commit
  `f913d40298eb59ec07dfa78305cc777720f9a775` (2026-10-20), R 4.6.1.
* LimitAware 0.1.4, source archive
  `dist/limitaware-0.1.4.tar.gz`, SHA-256
  `40530b36d7e5c19055294abc0c24268bcf3e550dc8e7fb1a6709cf77d4ee2ee4`.
* Inputs: the eight archived WQP Result-profile exports (2,875 rows). Source
  hashes are in `evaluation/frozen_hashes.json` and the per-export audit records.

## Common task, fixed before comparison

For each export, produce a per-row eligibility result and grouped analysis input
for the target analyte/fraction/method under the same reporting-limit policy:
routine environmental samples only; Total or Dissolved target fraction as fixed by
the export; reporting-limit roles only; below-LOQ excluded; estimated results
excluded; QC and field measurements excluded; duplicates retained; target unit ug/L.
The task covers detected values, non-detects, below-LOQ values, limits, units,
fractions, QC/field activities, duplicate handling, grouping and traceability.

## Workflows

### LimitAware

The native 0.1.4 `transform` command with the frozen policy. It writes canonical,
analysis, audit and methods-note outputs. No adapter.

### EPATADA unmatched

`TADA_AutoClean` -> `TADA_RunKeyFlagFunctions(clean = FALSE)` ->
`TADA_IDCensoredData`. The only input adapter maps the WQP Result profile to the
TADA template, adds a source-instance `ResultIdentifier` because the Result profile
has no `ResultIdentifier`, and preserves source row numbers. It does not alter
values or units. This is the unmatched workflow: native classification plus the same task-level filters, but no condition or missing-limit normalization.

### EPATADA matched

The unmatched workflow plus documented glue code to apply the same policy: normalize
condition-only non-detects for the identifier, exclude non-routine/QC and field
activities, distinguish estimated results, refuse DL rows without a numeric limit,
and restrict censoring to reporting-limit roles. The glue is recorded in
`run_end_to_end_matched.R`; its behavior is not credited to EPATADA.

## Results

| Workflow | Eligible rows | Difference from LimitAware |
| --- | ---: | --- |
| LimitAware 0.1.4 | 1,553 | reference |
| EPATADA unmatched | 1,577 | 9 LimitAware-eligible rows not classified censored; 33 LimitAware-ineligible rows admitted |
| EPATADA matched | 1,553 | none |

For the matched workflow, all 1,553 eligible sets, all censoring assignments, all
groups and all observation values agree exactly (maximum absolute value difference
0.0). Group identity agrees for all 1,553 rows after case/format normalisation.

Unmatched-workflow disagreements:

* 9 Illinois/Iowa rows have a documented `Not Detected` condition and a numeric
  reporting limit but no qualifier; `TADA_IDCensoredData` leaves them uncensored
  unless a non-detect placeholder is supplied.
* 22 Iowa `DL` rows with a value but no numeric limit become eligible in the native
  workflow; they are refusals in LimitAware because no bound exists.
* 2 estimated rows and 9 field-measurement rows are admitted natively under this
  package's flags; the matched policy excludes them explicitly.

These are workflow-definition and adapter issues, not evidence that either
implementation is generally wrong. The matched comparison shows that a competent
EPATADA workflow with glue can reproduce the preparation task; LimitAware's
differentiation is therefore the compact Python implementation, explicit per-row
refusals, versioned policy object and audit, not a unique mathematical capability.

## Capability matrix

Labels: native = supplied by the examined package function/workflow; configurable =
supplied through a documented package option; glue = requires a script outside the
package; absent = not present in the examined workflow; unassessed = not tested.

| Capability | LimitAware | EPATADA unmatched | EPATADA matched | Evidence |
| --- | --- | --- | --- | --- |
| WQP result retrieval | absent (delivered CSV) | native (`TADA_DataRetrieval`) | native | package index |
| WQX vocabulary application | native | native/configurable | native/configurable | references and executed flags |
| Limit-role-aware censoring | native | absent (combined Non-Detect flag) | glue | `TADA_IDCensoredData` source; matched adapter |
| Fraction/QC/value-type eligibility | native | glue (flags/filters) | glue | flags and matched filters |
| Below-LOQ policy | native | glue | glue | matched adapter |
| Duplicate policy | native/glue | native detection, policy separate | glue | `TADA_FindPotentialDuplicates*`; not exercised as a removal policy |
| Grouped analysis inputs | native | glue (`TADA_AggregateMeasurements`/comparable ID) | glue | group agreement |
| Per-row refusal status | native | absent | glue | matched output |
| Input digest and manifest | native | absent in examined workflow | glue | LimitAware audit; matched output not packaged |
| Deterministic rerun | native | package-dependent | package-dependent | LimitAware tests; EPATADA not fully replayed |

## Boundary

The comparison is on eight archived exports and one pinned commit. It does not
establish package-wide absence of capabilities, nor does it validate either tool's
semantic rules. The matched workflow's exact agreement is a reproducibility result,
not a correctness result.
