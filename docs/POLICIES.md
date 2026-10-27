# Interpretation policies

Four layers are kept apart: **raw** → **parsed** → **eligibility** →
**policy-dependent censoring**. A policy may change layers 3 and 4 only; it never
alters raw content.

## Policy fields (version 1.0)

| field | meaning | allowed |
| --- | --- | --- |
| `admissible_fractions` | fractions that may enter analysis | list, e.g. `["Total"]` |
| `admissible_methods` | methods allowed, or `null` for all | list / null |
| `units.target` / `units.conversions` | canonical unit and factors (`ug/l`, `ug/L`, `ng/l`, `ng/L`) | target must be in conversions |
| `censoring_limit_roles` | limit roles allowed to define censoring | subset of `reporting`, `mdl`, `loq`, `other` |
| `below_loq` | rows flagged "Present Below Quantification Limit" | `exclude` / `keep_as_detected` |
| `duplicates` | identical rows | `drop_identical` / `keep` |
| `qc_activities` | QC and field measurement activities | `exclude` / `keep` |
| `treat_missing_limit_for_detected` | detected rows without a limit | `allow` / `require` |

## Status precedence

1. `excluded_qc` — QC activity or field measurement
2. `excluded_fraction` — fraction not admissible
3. `excluded_method` — method not admissible
4. `excluded_value_type` — `ResultValueTypeName` other than "Actual"
5. `unsupported_unit` — result unit not convertible
6. `duplicate_identical` — same fields as an earlier row (when policy drops)
7. censored rows: `missing_limit`, `unsupported_limit_unit`, `excluded_limit_role`, else `eligible`
8. below-LOQ rows: `excluded_below_loq`, or `ambiguous_missing_value` if kept without a value
9. detected rows: `eligible`, or `missing_limit` if the policy requires one

Every row gets exactly one status; the counts appear in `audit.json` and the
methods note.

## Limit roles

`Method Detection Level` and `Method Detection Limit (MDL)` → `mdl`;
`Reporting limit by DQCALC`, `Lower Reporting Limit`, `Laboratory Reporting Level`,
`Minimum Reporting Level` → `reporting`; `Lower Quantitation Limit` → `loq`;
`Elevated Detection Limit` → `other`; `Estimated Detection Level` and
`Long Term Method Detection Level` → `mdl`; anything else → `unknown`.

The default policy uses only `reporting`. This is **not** a claim that reporting
limits are scientifically correct; it is one documented choice. ProUCL's user guide
shows the opposite convention is also used in practice (its WMW test maps
non-detects to the highest detection limit, Example 4-7, p. 102), which is why the
choice must be explicit.

## Below-LOQ results

"Present Below Quantification Limit" rows keep the reported value when the policy
says `keep_as_detected`; otherwise they are excluded. A row with no reported value
cannot be kept and becomes `ambiguous_missing_value`.

## Non-goals

No policy ranking, no automatic selection, no "best" estimate. Different policies
analyse different sets of measurements; the tool reports the difference.
