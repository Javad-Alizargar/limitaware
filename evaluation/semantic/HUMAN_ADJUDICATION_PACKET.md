# Blinded semantic adjudication packet (pending)

Status: **NOT COLLECTED**. No human expert review has been performed. This packet is
provided so an independent environmental-data specialist can adjudicate the rules
without seeing the implementation's answers. It must not be represented as completed
validation.

## Materials

* `reference_cases.csv` contains 15 delivered-record cases. The `Case_question`
  column states the issue but omits the software status and answer.
* Official sources for adjudication:
  * WQX domain values: Result Measure Qualifier, Result Detection Condition,
    Detection/Quantitation Limit Type, and Measure Unit
    (https://cdx.epa.gov/wqx/download/DomainValues/; accessed 2026-10-27).
  * US EPA, *WQX User Guidance: Detection Limits*, August 2025
    (https://www.epa.gov/system/files/documents/2025-09/wqxdetectionlimitsbestpracticesguide_final.pdf;
    accessed 2026-10-27).
  * WQP Result/search profile documentation
    (https://www.waterqualitydata.us/webservices_documentation/; accessed 2026-10-27).

## Task for each case

For each case, record:

1. Whether the row is analysable under the stated default policy
   (routine sample; Total fraction; reporting limits only; below-LOQ excluded;
   estimated results excluded; QC and field measurements excluded).
2. The censoring status (detected, left-censored, right-censored, unresolved).
3. The observation and unit if analysable.
4. The decisive source passage (document, section/table, accessed date).
5. Confidence and any agency-specific convention that would change the answer.

## Blinding and reporting

The adjudicator should not read `expected.json`, `results.json`, the source code, or
the manuscript's result section before returning answers. Answers should be returned
as a CSV keyed by `case_id`, with `decision`, `censored`, `observation`, `unit`,
`source_locator`, `confidence`, and `notes`. Agreement, disagreement and unresolved
conventions should be reported without replacing the software's frozen outputs.
