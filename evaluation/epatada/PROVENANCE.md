# EPATADA comparison provenance

* Package: EPATADA 0.0.1 (DESCRIPTION), GitHub USEPA/EPATADA, branch `develop`,
  commit `f913d40298eb59ec07dfa78305cc777720f9a775`, commit date 2026-10-20.
* Accessed and installed 2026-10-26 with R 4.6.1 via
  `remotes::install_github("USEPA/EPATADA@f913d40298eb59ec07dfa78305cc777720f9a775", dependencies=TRUE)`.
  Installation completed with exit 0 (`/tmp/epatada_install.log`). The installed
  `packageDescription("EPATADA")$RemoteSha` is `f913d40298eb59ec07dfa78305cc777720f9a775`,
  matching the pinned commit; no moving branch is used for reproduction.
* Documentation: https://usepa.github.io/EPATADA/ and
  `reference/TADA_IDCensoredData.html` (accessed 2026-10-26).
* Source inspected: `R/CensoredDataSuite.R`, `R/WQPWQXATTAINSCSTRefs.R`,
  `R/UnitConversions.R` on branch `develop`.
* Executed: `TADA_IDCensoredData()` on adapted Illinois, Minnesota, Indiana,
  Wisconsin, Mississippi and Iowa result exports. Adapter:
  `run_comparison.R`; it creates a source-instance `ResultIdentifier`
  (`source_row_<line>`) because the WQP Result profile has no ResultIdentifier.
  This is documented and is not a WQP identifier.
* Unit reference executed: `TADA_GetMeasureUnitRef()` returns `ng/L -> ug/L`
  factor 1e-3 and `ug/L -> ug/L` factor 1. Lowercase spellings (`ng/l`, `ug/l`)
  were not present in that reference table.
* Raw outputs: `<export>_flags.csv`; per-row counts in `comparison_counts.json`.
