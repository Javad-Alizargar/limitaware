# End-to-end EPATADA workflow for the matched preparation task.
# EPATADA 0.0.1, pinned commit f913d402. Inputs are archived WQP Result-profile
# CSV files. The adapter maps WQP slash-named fields to the TADA template and adds
# a source-instance ResultIdentifier. It does not alter values or units.
suppressMessages({library(EPATADA); library(dplyr)})
args <- commandArgs(TRUE)
if (length(args) < 3) stop("usage: run_end_to_end.R input.csv output.csv target_fraction")
infile <- args[1]; outfile <- args[2]; target_fraction <- toupper(args[3])
raw <- read.csv(infile, stringsAsFactors = FALSE, check.names = FALSE)
raw$ResultIdentifier <- paste0("source_row_", seq_len(nrow(raw)) + 1L)

map <- c(
 'ResultMeasure.MeasureUnitCode'='ResultMeasure/MeasureUnitCode',
 'DetectionQuantitationLimitMeasure.MeasureValue'='DetectionQuantitationLimitMeasure/MeasureValue',
 'DetectionQuantitationLimitMeasure.MeasureUnitCode'='DetectionQuantitationLimitMeasure/MeasureUnitCode',
 'ResultDepthHeightMeasure.MeasureValue'='ResultDepthHeightMeasure/MeasureValue',
 'ResultDepthHeightMeasure.MeasureUnitCode'='ResultDepthHeightMeasure/MeasureUnitCode',
 'ActivityDepthHeightMeasure.MeasureValue'='ActivityDepthHeightMeasure/MeasureValue',
 'ActivityDepthHeightMeasure.MeasureUnitCode'='ActivityDepthHeightMeasure/MeasureUnitCode',
 'ActivityTopDepthHeightMeasure.MeasureValue'='ActivityTopDepthHeightMeasure/MeasureValue',
 'ActivityTopDepthHeightMeasure.MeasureUnitCode'='ActivityTopDepthHeightMeasure/MeasureUnitCode',
 'ActivityBottomDepthHeightMeasure.MeasureValue'='ActivityBottomDepthHeightMeasure/MeasureValue',
 'ActivityBottomDepthHeightMeasure.MeasureUnitCode'='ActivityBottomDepthHeightMeasure/MeasureUnitCode',
 'ResultAnalyticalMethod.MethodName'='ResultAnalyticalMethod/MethodName',
 'ResultAnalyticalMethod.MethodDescriptionText'='MethodDescriptionText',
 'ResultAnalyticalMethod.MethodIdentifier'='ResultAnalyticalMethod/MethodIdentifier',
 'ResultAnalyticalMethod.MethodIdentifierContext'='ResultAnalyticalMethod/MethodIdentifierContext',
 'SampleCollectionMethod.MethodIdentifier'='SampleCollectionMethod/MethodIdentifier',
 'SampleCollectionMethod.MethodIdentifierContext'='SampleCollectionMethod/MethodIdentifierContext',
 'SampleCollectionMethod.MethodName'='SampleCollectionMethod/MethodName',
 'DataQuality.PrecisionValue'='PrecisionValue')
tmpl <- TADA_GetTemplate()
d <- as.data.frame(matrix(NA, nrow=nrow(raw), ncol=ncol(tmpl))); names(d) <- names(tmpl)
for (nm in names(d)) {
  src <- if (nm %in% names(map)) map[[nm]] else nm
  if (src %in% names(raw)) d[[nm]] <- raw[[src]]
}
d$ResultIdentifier <- raw$ResultIdentifier
d$source_row <- seq_len(nrow(raw)) + 1L
d$ActivityStartDateTime <- as.POSIXct(paste(d$ActivityStartDate,
  ifelse(is.na(d$ActivityStartTime.Time), "00:00:00", d$ActivityStartTime.Time)), tz="UTC")

x <- TADA_AutoClean(d)
x <- TADA_RunKeyFlagFunctions(x, clean = FALSE)
# Adapter normalization for documented WQX conditions that the native identifier
# does not classify without a non-detect placeholder/qualifier. This is glue code,
# not credited to EPATADA or LimitAware.
cond_pre <- tolower(trimws(ifelse(is.na(x$ResultDetectionConditionText), "", x$ResultDetectionConditionText)))
rv_blank <- is.na(x$ResultMeasureValue) | !nzchar(trimws(as.character(x$ResultMeasureValue)))
nd_conditions <- c("not detected", "below reporting limit", "not detected at detection limit", "not detected at reporting limit")
x$ResultMeasureValue[cond_pre %in% nd_conditions & rv_blank] <- "ND"
x <- TADA_IDCensoredData(x)
if (!"TADA.CensoredData.Flag" %in% names(x)) x$TADA.CensoredData.Flag <- "Uncensored"
x$TADA.CensoredData.Flag[is.na(x$TADA.CensoredData.Flag)] <- "Uncensored"

# Matched P0 policy filters. These are explicit glue, not credited to EPATADA.
frac <- ifelse(is.na(x$TADA.ResultSampleFractionText), "", toupper(trimws(x$TADA.ResultSampleFractionText)))
qcflag <- ifelse(is.na(x$TADA.ActivityType.Flag), "", x$TADA.ActivityType.Flag)
vtype <- ifelse(is.na(x$ResultValueTypeName), "", tolower(trimws(x$ResultValueTypeName)))
cond <- ifelse(is.na(x$ResultDetectionConditionText), "", tolower(trimws(x$ResultDetectionConditionText)))
qual <- ifelse(is.na(x$MeasureQualifierCode), "", toupper(trimws(x$MeasureQualifierCode)))
below <- grepl("below quant", cond) | grepl("bql|brl|ltgte|2-5b|<2b", qual)
reporting_types <- c("Minimum Reporting Level", "Lower Reporting Limit", "Reporting limit",
  "Reporting limit by DQCALC", "Interim Reporting Level", "Laboratory Reporting Level",
  "Lab Reporting Limit, NA", "Blank-adjusted reporting limit", "Historical Lower Reporting Limit")
is_reporting <- is.na(x$DetectionQuantitationLimitTypeName) | x$DetectionQuantitationLimitTypeName %in% reporting_types
num <- suppressWarnings(as.numeric(x$TADA.ResultMeasureValue))
has_limit <- !is.na(x$TADA.DetectionQuantitationLimitMeasure.MeasureValue) &
  nzchar(ifelse(is.na(x$TADA.DetectionQuantitationLimitMeasure.MeasureUnitCode), "", x$TADA.DetectionQuantitationLimitMeasure.MeasureUnitCode))
status <- rep("eligible", nrow(x)); reason <- rep("", nrow(x))
status[qcflag != "Non_QC" | x$ActivityTypeCode == "Field Msr/Obs"] <- "excluded_qc"; reason[qcflag != "Non_QC" | x$ActivityTypeCode == "Field Msr/Obs"] <- "activity type not Non_QC"
status[status=="eligible" & frac != target_fraction] <- "excluded_fraction"; reason[status=="excluded_fraction"] <- "target fraction differs"
status[status=="eligible" & vtype == "estimated"] <- "excluded_estimated"; reason[status=="excluded_estimated"] <- "value type is Estimated"
status[status=="eligible" & vtype != "actual" & vtype != "estimated"] <- "excluded_value_type"; reason[status=="excluded_value_type"] <- "value type is not Actual"
status[status=="eligible" & grepl("(^|;)J(;|$)", qual)] <- "excluded_estimated"; reason[status=="excluded_estimated"] <- "estimated qualifier J"
status[status=="eligible" & below] <- "excluded_below_loq"; reason[status=="excluded_below_loq"] <- "below-LOQ record"
cens <- x$TADA.CensoredData.Flag == "Non-Detect"
status[status=="eligible" & cens & !is_reporting] <- "excluded_limit_role"; reason[status=="excluded_limit_role"] <- "limit role is not reporting"
status[status=="eligible" & cens & !has_limit] <- "missing_limit"; reason[status=="missing_limit"] <- "censored record has no numeric limit"
status[status=="eligible" & !cens & grepl("(^|;)DL(;|$)", qual) & !has_limit] <- "missing_limit"; reason[status=="missing_limit"] <- "DL qualifier without a numeric limit"
status[status=="eligible" & !cens & is.na(num)] <- "missing_value"; reason[status=="missing_value"] <- "detected record has no numeric value"
status[status=="eligible" & !cens & grepl("conflict", tolower(x$TADA.CensoredData.Flag))] <- "conflicting"; reason[status=="conflicting"] <- "condition/limit conflict"

group <- paste(x$TADA.CharacteristicName, frac,
  ifelse(is.na(x$ResultAnalyticalMethod.MethodIdentifier), "", x$ResultAnalyticalMethod.MethodIdentifier), sep=" | ")
obs <- ifelse(cens, x$TADA.DetectionQuantitationLimitMeasure.MeasureValue, num)
out <- data.frame(
  source_row = x$source_row,
  result_identifier = x$ResultIdentifier,
  status = status,
  reason = reason,
  censored = cens,
  observation = obs,
  result_value_epatada = num,
  limit_value_epatada = x$TADA.DetectionQuantitationLimitMeasure.MeasureValue,
  unit_epatada = x$TADA.ResultMeasure.MeasureUnitCode,
  group_epatada = group,
  fraction = frac,
  characteristic = x$TADA.CharacteristicName,
  method = x$ResultAnalyticalMethod.MethodIdentifier,
  limit_type = x$DetectionQuantitationLimitTypeName,
  limit_role_reporting = is_reporting,
  tada_flag = x$TADA.CensoredData.Flag,
  tada_qc_flag = qcflag,
  tada_fraction_flag = x$TADA.SampleFraction.Flag,
  tada_unit_flag = x$TADA.ResultUnit.Flag,
  stringsAsFactors = FALSE)
write.csv(out, outfile, row.names = FALSE)
cat("rows", nrow(out), "statuses\n"); print(table(out$status, useNA="ifany"))
