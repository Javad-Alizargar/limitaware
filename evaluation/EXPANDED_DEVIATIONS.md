# Expanded evaluation — deviations log

Recorded in order. Empty until the first deviation.

## D1. Pre-run contract repair (2026-10-26)

Raw inspection of the selected exports (before any transform) showed three
documented WQX conventions that 0.1.3 did not implement: the `ng/L` unit spelling,
the `DL` qualifier, and the condition `Below Reporting Limit`. The WQX domain value
downloads were retrieved from `cdx.epa.gov` and resolve `DL` as a non-detect at or
above the MDL. Version 0.1.4 adds these documented mappings (with tests); 0.1.3
outputs are retained as `results_preRepair_0.1.3/` and reported as the pre-repair
contract result.

## D2. Selection tie and baseline filename defect (2026-10-26)

Missouri returned 45 Total and 45 Dissolved rows; the protocol's modal-fraction rule
does not define a tie, so it was excluded after selection (five held-out exports, not
six). The baseline script wrote method names containing `/` into subdirectories; it
was repaired to slug the name and append a key hash before any comparison.

## D3. Downstream eligibility rule (2026-10-26)

The protocol required at least two distinct limit values for a KM fit. After seeing
that several groups have a single limit with many censored observations, the rule was
relaxed to at least 8 detected values, at least 1 censored value and at least 1
distinct limit. A single-limit KM fit is identifiable; the number of distinct limits
is reported alongside each estimate. No fit is forced where detects are insufficient.
