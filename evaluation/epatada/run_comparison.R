# Bounded EPATADA comparison on archived LimitAware inputs.
# EPATADA version 0.0.1, GitHub USEPA/EPATADA develop commit f913d402 (2026-10-20).
suppressMessages({library(EPATADA); library(dplyr)})
args <- commandArgs(TRUE)
infile <- args[1]; outfile <- args[2]
raw <- read.csv(infile, stringsAsFactors = FALSE, check.names = FALSE)

# Documented adapter: the WQP Result profile has no ResultIdentifier. A stable
# source-instance id is created from the CSV line number; it is not a WQP id.
raw$ResultIdentifier <- paste0("source_row_", seq_len(nrow(raw)) + 1L)
num <- function(x) suppressWarnings(as.numeric(gsub(",", "", trimws(as.character(x)))))
d <- data.frame(
  ResultIdentifier = raw$ResultIdentifier,
  ResultMeasureValue = raw[["ResultMeasureValue"]],
  ResultDetectionConditionText = raw[["ResultDetectionConditionText"]],
  DetectionQuantitationLimitTypeName = raw[["DetectionQuantitationLimitTypeName"]],
  TADA.ResultMeasureValueDataTypes.Flag = ifelse(
    is.na(num(raw[["ResultMeasureValue"]])) | trimws(as.character(raw[["ResultMeasureValue"]])) == "",
    "NA - Not Available",
    ifelse(tolower(trimws(raw[["ResultValueTypeName"]])) == "estimated", "Estimated", "Actual")),
  TADA.ResultMeasureValue = num(raw[["ResultMeasureValue"]]),
  TADA.ResultMeasure.MeasureUnitCode = raw[["ResultMeasure/MeasureUnitCode"]],
  TADA.DetectionQuantitationLimitMeasure.MeasureValue = num(raw[["DetectionQuantitationLimitMeasure/MeasureValue"]]),
  TADA.DetectionQuantitationLimitMeasure.MeasureUnitCode = raw[["DetectionQuantitationLimitMeasure/MeasureUnitCode"]],
  MeasureQualifierCode = raw[["MeasureQualifierCode"]],
  stringsAsFactors = FALSE
)
# EPATADA derives qualifier flags from MeasureQualifierCode when present.
out <- tryCatch(TADA_IDCensoredData(d), error = function(e) {
  cat("EPATADA_ERROR:", conditionMessage(e), "\n")
  NULL
})
if (is.null(out)) quit(status = 2)
keep <- c("ResultIdentifier", "TADA.CensoredData.Flag", "ResultMeasureValue",
          "ResultDetectionConditionText", "DetectionQuantitationLimitTypeName",
          "MeasureQualifierCode", "TADA.ResultMeasureValueDataTypes.Flag")
write.csv(out[, intersect(keep, names(out))], outfile, row.names = FALSE)
cat("rows:", nrow(out), "\n")
print(table(out$TADA.CensoredData.Flag, useNA = "ifany"))
