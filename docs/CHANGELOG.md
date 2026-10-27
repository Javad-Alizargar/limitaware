# Changelog

## 0.1.4 (2026-10-26)

Documented WQX vocabulary added after held-out evaluation:
`DL` qualifier (left-censored), `Below Reporting Limit` condition (censored),
`Minimum Reporting Level` (reporting role), `Estimated Detection Level` and
`Long Term Method Detection Level` (mdl role), and the `ng/L` unit spelling.
Six regression tests added (62 total). Held-out results from 0.1.3 are preserved
separately; 0.1.4 is the version reported in the manuscript.

## 0.1.3

Unit requirement depends on the evidence: inline-limit censoring needs the limit
unit; embedded bounds and numeric results need the result unit; comparisons need
both.

## 0.1.2

Grouped outputs, manifest reconciliation and qualifier conflict handling.
