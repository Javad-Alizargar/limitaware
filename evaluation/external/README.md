# Frozen external evaluation (post-inspection amendment)

This directory contains two retained external WQP Result exports and one empty query,
frozen after the 0.1.4 implementation was hashed. It is an amendment, not part of the
original five-export holdout, and it is not a probability sample.

Files:

* `EXTERNAL_PROTOCOL.md` – prespecified queries, retention rule and reporting limits.
* `freeze.json` – implementation archive and SHA-256 hashes.
* `download_manifest.json` / `selection_log.json` – URLs, sizes, hashes, organizations.
* `policies/reporting_dissolved_P0.json`, `policies/reporting_extractable_P0.json` –
  configuration objects used for the two retained exports. They change only the
  admissible fraction and use reporting limits, below-LOQ exclusion, estimated-result
  exclusion, QC exclusion and duplicate retention.
* `data/` – unchanged delivered CSVs (Vermont empty).
* `results/<stem>/` – canonical, analysis, audit, manifest and methods note from the
  frozen 0.1.4 source.
* `results_summary.json` – row counts, statuses, groups and NADA Kaplan–Meier fits.

Results: Georgia (61 rows) had 45 eligible (26 censored), 7 excluded limit roles and
9 excluded QC; its group mean was 0.0185 ug/L (unadjusted 95% interval -0.0126 to
0.0496). Oregon (348) had 196 eligible (180 censored), 62 unresolved (5 ambiguous
qualifiers, 57 conflicting qualifiers), 42 excluded fractions and 48 excluded QC; its
group mean was 0.1260 ug/L (0.1074 to 0.1446), with median not identified. No transform
errors occurred. The negative Georgia lower bound is retained; it is not a population
interval.

Vermont returned no rows and is reported as not retained. No software behavior was
changed after the freeze. Human semantic adjudication remains pending.
