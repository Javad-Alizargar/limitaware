# NADA Kaplan-Meier summary for one prepared group. Fixed 15-field schema.
# Usage: Rscript nada_group_summary.R analysis.csv export policy "group"
suppressMessages(library(NADA))
a <- commandArgs(TRUE)
fields <- c("export","policy","group","n","n_detected","n_censored",
            "distinct_censoring_limits","median","mean","mean_se","mean_lcl",
            "mean_ucl","fit_status","warning","failure_reason")
cat(paste(fields, collapse="\t"), "\n", sep="")
row <- function(..., status, warning="NA", failure="NA") {
  vals <- c(a[2], a[3], a[4], ...)
  cat(paste(c(vals, status, warning, failure), collapse="\t"), "\n", sep="")
}
NAV <- "NA"
d <- tryCatch(read.csv(a[1], stringsAsFactors=FALSE), error=function(e) NULL)
if (is.null(d) || !all(c("obs","censored") %in% names(d))) {
  row(NAV,NAV,NAV,NAV,NAV,NAV,NAV,NAV,NAV, status="r_error",
      warning="input could not be read", failure="missing obs/censored columns")
  quit(save="no", status=0)
}
obs <- suppressWarnings(as.numeric(d$obs))
cen <- suppressWarnings(as.logical(toupper(as.character(d$censored))))
ok <- is.finite(obs) & !is.na(cen)
obs <- obs[ok]; cen <- cen[ok]
n <- length(obs); ncen <- sum(cen); ndet <- n - ncen
limits <- sort(unique(signif(obs[cen], 12)))
ndlim <- length(limits)
base <- c(n, ndet, ncen, ndlim)
if (n < 3 || ndet < 8 || ncen < 1 || ndlim < 1) {
  reason <- if (n < 3) "n<3" else if (ndet < 8) "n_detected<8" else if (ncen < 1) "n_censored<1" else "no distinct limit"
  row(base, NAV,NAV,NAV,NAV,NAV, status="skipped_insufficient_detects",
      warning="fit screening failed", failure=reason)
  quit(save="no", status=0)
}
res <- tryCatch({
  f <- cenfit(obs, cen); m <- mean(f)
  lcl_name <- grep("LCL", names(m), value=TRUE)[1]
  ucl_name <- grep("UCL", names(m), value=TRUE)[1]
  list(med=as.numeric(median(f)), mean=unname(m[["mean"]]), se=unname(m[["se"]]),
       lcl=unname(m[[lcl_name]]), ucl=unname(m[[ucl_name]]))
}, error=function(e) list(err=conditionMessage(e)))
if (!is.null(res$err)) {
  row(base, NAV,NAV,NAV,NAV,NAV, status="r_error", warning="cenfit failed",
      failure=gsub("[\t\n]", " ", res$err)); quit(save="no", status=0)
}
num <- c(res$mean,res$se,res$lcl,res$ucl)
if (any(!is.finite(num))) {
  row(base, NAV,NAV,NAV,NAV,NAV, status="invalid_nonfinite",
      warning="non-finite estimate", failure="NADA returned a non-finite value")
  quit(save="no", status=0)
}
if (!is.finite(res$med)) {
  row(base, NAV,res$mean,res$se,res$lcl,res$ucl, status="ok_median_not_identified",
      warning="median not identified (curve does not cross 0.5)", failure="NA")
} else {
  row(base, res$med,res$mean,res$se,res$lcl,res$ucl, status="ok", warning="NA", failure="NA")
}
