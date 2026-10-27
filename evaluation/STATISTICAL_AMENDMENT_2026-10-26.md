# Statistical amendment — 2026-10-26

Written before the revised downstream summaries and integrated into the manuscript.
It records which earlier choices were made after inspecting results.

## A. Estimands

Every downstream summary describes a **record-level distribution within one
state/analyte/year export and one homogeneous group** (analyte, fraction, method),
in µg/L. It does not estimate a monitoring population, a site population or a
regulatory exceedance probability. Records are eligible WQP results under a declared
preparation policy; the same policy may change the included records, and therefore
the estimand's population.

For each group we report: analyte, fraction, method, export and year; n records;
n activities; n monitoring locations; n organisations; n sampling dates; censored
records; distinct limit values; and the estimator and its assumptions.

Repeat measurements: in these exports each activity contributes one result per group
(`records = activities`). Repeats occur across dates and locations, so records are
clustered within locations, not independent. The number of locations is the relevant
clustering scale; single-location groups support only a site-specific description.

## B. Dependence and sampling (computed)

| Export / group | Records = activities | Locations | Organisations | Dates | Censored | Distinct limits |
| --- | --- | --- | --- | --- | --- | --- |
| Illinois Atrazine/Total/8141 | 181 | 48 | 1 | 105 | 66 | 1 |
| Minnesota 2,4-D/Total | 630 | 248 | 1 | 130 | 271 | 1 |
| Wisconsin Metolachlor/Total | 265 | 79 | 1 | 58 | 166 | 1 |
| Mississippi Atrazine/Dissolved/LCM60 | 52 | 5 | 1 | 47 | 1 | 1 |
| Iowa Atrazine/Total/8141 | 23 | 1 | 1 | 23 | 15 | 1 |
| Iowa Atrazine/Total/8270B(W) | 183 | 59 | 1 | 29 | 0 | 0 |
| New York Metolachlor/Dissolved/LCM60 | 109 | 65 | 1 | 65 | 62 | 1 |
| Ohio Prometon/Dissolved/LCM60 | 13 | 1 | 1 | 13 | 2 | 1 |

No export contains more than one organisation in an analysed group. Several groups
have very few locations (Mississippi 5, Iowa 8141 1, Ohio 1). Record-level confidence
intervals would therefore overstate information; no population intervals are claimed.
Wilson intervals are not used for these dependent records.

## C. Kaplan–Meier audit (NADA 1.6-1.2)

`cenfit` flips left-censored observations and calls `survival::survfit`; the reported
mean is the area under the fitted survival curve from `min(0, first event time)` to
the largest observed time (a truncated area over the observed range, mapped back to
input units), with a normal-approximation interval based on a Greenwood-type variance. The median is the
0.5 quantile of the fitted ECDF and is returned as `NA` when the curve does not cross
0.5. The method assumes independent/random censoring and that each censored value's
limit is the correct bound; it does not use the number of locations or organisations.

Screening rule (revised and disclosed): fit only if a group has at least 8 detected
values, at least 1 censored value and at least 1 distinct limit. This is a screening
rule, not a validity test. All fitted summaries are labelled descriptive; intervals are unadjusted for site
dependence and rely on independent/random censoring. Single-location groups are
explicitly site-specific.

## D. Uncertainty and policy comparison

* Report NADA's 95% interval as a model-based interval conditional on the group,
  censoring model and limit assignment. Do not call it population uncertainty.
* Do not infer a policy difference from overlap or non-overlap of separate intervals.
  The earlier sentence that used overlapping intervals as evidence was removed.
* Policy comparisons report: change in included records; paired absolute and relative
  differences in the median and area-under-curve mean for the same group; and the change in
  composition (records/activities/locations). No significance test is added.
* No bootstrap is used: with 1–5 locations in several groups, a cluster bootstrap
  would not be credible, and a record bootstrap would ignore dependence.

## E. Choices made after inspection (disclosed)

* The ≥8-detected screening threshold and the original ≥2-limit rule were chosen
  before the amended analysis; the limit rule was relaxed to ≥1 after group inspection
  (deviation D3). The manuscript reports this.
* P0 and P1 were pre-specified; P2–P5 were added as one-setting controls. Their null
  results are reported.
* The Kaplan–Meier summaries are descriptive; no policy is declared preferable.
* Earlier drafts described separate 95% intervals as overlapping and implied no
  difference. That inference is removed; only the paired point differences are shown.

## F. Consequences for the manuscript

* Table 4 gains the number of locations and organisations and states the estimand.
* The abstract and §5.4 no longer imply population inference or test the policy
  difference via interval overlap.
* A single-location group (Iowa 8141, Ohio) is described as site-specific.
* Median "not identified" remains reported, not imputed.
