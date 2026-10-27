# Independent reconstruction of ONE analysis group from the published canonical table.
# Usage: Rscript limitaware_reference_from_canonical.R canonical.csv analyte fraction method analysis_file
suppressMessages(library(NADA))
a <- commandArgs(TRUE)
canon <- read.csv(a[1], stringsAsFactors = FALSE, na.strings = c("", "NA"))
analyte <- a[2]; fraction <- a[3]; method <- a[4]; gen <- read.csv(a[5], stringsAsFactors = FALSE)
elig <- canon[canon$analysis_eligible == "true" & canon$analyte == analyte &
              canon$fraction == fraction & canon$method == method, ]
obs <- ifelse(elig$censored == "true", elig$limit_value, elig$value)
ref <- data.frame(obs = obs, censored = elig$censored, result_uid = elig$result_uid)
stopifnot(!any(is.na(ref$obs)), nrow(gen) == nrow(ref),
          all(gen$result_uid == ref$result_uid), max(abs(gen$obs - ref$obs)) < 1e-12)
fg <- cenfit(gen$obs, as.logical(toupper(as.character(gen$censored))))
fr <- cenfit(ref$obs, as.logical(toupper(as.character(ref$censored))))
cat(sprintf("group=%s;%s;%s n=%d censored=%d diff=%.3e\n", analyte, fraction, method,
            nrow(gen), sum(gen$censored),
            abs(as.numeric(mean(fg))[1] - as.numeric(mean(fr))[1])))
stopifnot(abs(as.numeric(mean(fg))[1] - as.numeric(mean(fr))[1]) < 1e-9)
