# Input contract — `wqp-result-csv/2026-10`

## Supported profile

| item | value |
| --- | --- |
| Source | Water Quality Portal, `GET /data/Result/search` |
| Format | CSV (`mimeType=csv&zip=no`) |
| Profile | default result profile (no `dataProfile` parameter) |
| Data model | one row = one reported result, with the detection/quantitation limit **inline** |
| Files required | **one**: the Result CSV |
| Optional | a `ResultDetectionQuantitationLimit` CSV, for consistency checks only |

The contract version is recorded in every `audit.json`.

## Why the limits export is not required — and not sufficient

The Result CSV contains `DetectionQuantitationLimitTypeName`,
`DetectionQuantitationLimitMeasure/MeasureValue` and its unit on the same row as
the result. A separate limits export is therefore redundant for the inline case.

It is also not joinable: the Result CSV has **no `ResultIdentifier`**, and the XML
profile tested in this project does not expose one either, while the limits export
is keyed by `ResultIdentifier`. Joining on `ActivityIdentifier` alone would attach
one analyte's limit to another result whenever an activity contains several
analytes, and would duplicate results when an activity has more than one limit
(observed: 920 limit rows across 892 activities, max 2 per activity).

`limitaware` therefore:

* uses the inline limit;
* accepts an optional limits export **only** to report ambiguous keys, never to
  attach a limit;
* keeps ambiguous matches unresolved.

## Required columns

```
OrganizationIdentifier
ActivityIdentifier
ActivityTypeCode
CharacteristicName
ResultSampleFractionText
ResultMeasureValue
ResultMeasure/MeasureUnitCode
ResultDetectionConditionText
ResultAnalyticalMethod/MethodIdentifier
DetectionQuantitationLimitTypeName
DetectionQuantitationLimitMeasure/MeasureValue
DetectionQuantitationLimitMeasure/MeasureUnitCode
```

Missing any of these stops the run with the list of missing columns.

## Identifiers

| entity | field | note |
| --- | --- | --- |
| organization | `OrganizationIdentifier` | used in `result_uid` |
| activity (sample event) | `ActivityIdentifier` | not unique per result |
| result | *none* | `result_uid` is derived: SHA-1 of organisation and CSV line number (12 hex chars) |
| analyte | `CharacteristicName` | |
| fraction | `ResultSampleFractionText` | never pooled |
| method | `ResultAnalyticalMethod/MethodIdentifier` | never pooled |
| limit | inline type/value/unit | one per row in this profile |

`result_uid` is stable for a given file; it is not a WQP identifier and must not be
presented as one.

## Duplicates

Rows are compared on the complete delivered record with generated fields removed.
A difference in any delivered field makes two rows distinct. Identical duplicates
are flagged with the row number of the kept record when the policy says
`drop_identical`; otherwise they are kept and flagged. Nothing is merged silently.


## Documented WQX vocabulary (v0.1.4)

The following entries are taken from the official WQX domain value downloads
(`https://cdx.epa.gov/wqx/download/DomainValues/`, accessed 2026-10-26):

| field | value | meaning used |
| --- | --- | --- |
| `MeasureQualifierCode` | `DL` | not detected at or above the method detection limit; treated as left-censored |
| `ResultDetectionConditionText` | `Below Reporting Limit` | below laboratory reporting limits; treated as censored at the inline limit |
| limit type | `Minimum Reporting Level` | reporting limit role |
| limit type | `Estimated Detection Level` | method-detection-level role |
| limit type | `Long Term Method Detection Level` | method-detection-level role |
| unit | `ng/L` | identical to `ng/l`, factor 0.001 to µg/L |

A `DL` record without a numeric limit is refused as `missing_limit`: the qualifier
establishes that the value is not an observation but does not supply the threshold.
