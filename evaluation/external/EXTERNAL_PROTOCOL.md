# Post-inspection, software-frozen external evaluation protocol (2026-10-27)

## Status and scope

This is a post-inspection amendment, not part of the original frozen evaluation. It
tests the unchanged LimitAware 0.1.4 implementation on exports that were not used to
develop or repair the interpretation rules. It does not convert the five inspected
exports into untouched holdouts, and it is not a probability sample of the Water
Quality Portal.

## Selection before outcome inspection

Three state/analyte/year queries were specified before any result value was examined:

1. Vermont, Atrazine, calendar year 2023.
2. Georgia, Metolachlor, calendar year 2023.
3. Oregon, 2,4-D, calendar year 2023.

The states and analytes differ from the development/held-out states. Query URLs use
the public WQP `Result/search` CSV endpoint (`mimeType=csv&zip=no`). A candidate is
retained if the response is HTTP 200, has at least 20 data rows, is no larger than
2 MB, and has a parseable WQP Result profile. Selection is by provider, geography,
analyte and file feasibility, not by observed eligibility or values. Vermont returned
zero rows and was not retained. Georgia delivered only Dissolved results; Oregon
delivered Extractable and Dissolved results, and the modal Extractable fraction was
fixed as the target before value inspection. No substitutions were made after values
were inspected.

## Frozen implementation

* LimitAware source archive: `dist/limitaware-0.1.4.tar.gz` (SHA-256 recorded in
  `evaluation/external/freeze.json`).
* Public verification script and held-out policies are unchanged.
* The implementation is run with the default `reporting-limit-total` policy
  (`P0`) and a `reporting-dissolved` policy only where the export's target fraction is
  Dissolved. The target fraction is fixed from the query/record distribution before
  outcome inspection; no policy is selected after seeing downstream estimates.

## Metrics and reporting

For each export: source rows; eligible, excluded and unresolved counts; reason counts;
group identities; censored/detected counts; distinct limits; fit status under NADA
Kaplan–Meier; and refusal examples. Higher eligibility is not treated as correctness.
Any implementation defect found after execution will be preserved as a frozen result
and followed by a dated amendment; the frozen run will not be silently overwritten.
