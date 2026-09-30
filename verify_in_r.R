# ---------------------------------------------------------------------------
# Devan Cantrell Addison-Turner, ORCID 0000-0002-2511-3680
# Department of Civil and Environmental Engineering, Stanford University
#
# From the reproduction package for "An optically independent administrative
# reference for validating built-surface products, and the tree-canopy bias it
# reveals", a manuscript prepared for GIScience & Remote Sensing. Not yet
# published; cite the repository until it is. Citation metadata: CITATION.cff.
#
# https://github.com/devanaddisonturner/Canopy-Bias-Nevada
# Code MIT, released data CC0 1.0.
# ---------------------------------------------------------------------------
# ============================================================================
# verify_in_r.R
#
# An INDEPENDENT reimplementation, in R, of the manuscript's headline results.
#
# WHY THIS EXISTS
# ---------------
# The package already computes every headline number twice, once in JavaScript
# in the browser during extraction and once in Python from the written CSV. This
# is a third implementation in a third language, written from the paper's own
# definitions rather than by translating make_tables.py line by line. Agreement
# between three independent implementations is a stronger claim than a single
# harness re-running itself, and R is the language a large part of this
# manuscript's likely readership actually uses.
#
# It is not a port of the 440-assertion harness and does not try to be. It
# reproduces the results a reader would check first: the analysis sample, the
# headline canopy coefficients on both outcomes, the HC1 and Conley standard
# errors, the mean bound and the breach rate.
#
# BASE R ONLY. No tidyverse, no sandwich, no conleyreg, no install step. The
# Conley spatial HAC is implemented here from the Bartlett kernel rather than
# taken from a package, so it is genuinely independent of conley.py rather than
# two callers of one library.
#
#   Rscript verify_in_r.R
#   Rscript verify_in_r.R /path/to/nevada_canopy_bias_rowlevel.csv
#
# Exits non-zero if any value disagrees with the manuscript.
# ============================================================================

args <- commandArgs(trailingOnly = TRUE)

# Resolve the CSV relative to this script, so the script runs from any working
# directory: Rscript from elsewhere, source() in RStudio, or a double-click.
this_file <- sub("^--file=", "",
                 grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE))
here <- if (length(this_file) == 1) dirname(normalizePath(this_file)) else getwd()
csv <- if (length(args) >= 1) args[1] else file.path(here, "nevada_canopy_bias_rowlevel.csv")

if (!file.exists(csv)) {
  stop(sprintf("cannot find %s\n  pass the path as an argument:\n  Rscript verify_in_r.R /path/to/nevada_canopy_bias_rowlevel.csv", csv))
}

cat("verify_in_r.R  an independent R reimplementation of the headline results\n")
cat(sprintf("  R %s.%s\n", R.version$major, R.version$minor))
cat(sprintf("  reading %s\n\n", csv))

d <- read.csv(csv, stringsAsFactors = FALSE)

# ---------------------------------------------------------------- definitions
# Equation 2's ceiling: a cell cannot be more than wholly impervious, so the
# bound is truncated at 100 percent of cell area, and every breach indicator is
# derived from the TRUNCATED bound. Getting this wrong is the defect the project
# record calls the +0.3113 versus +0.3119 discrepancy, so it is stated here
# rather than inherited.
d$imp_floor_raw <- d$imp_floor_px
d$imp_floor_px  <- pmin(d$imp_floor_px, 100)
d$floorA_raw    <- d$floorA
d$floorA        <- pmin(d$floorA, 100)
d$below         <- as.numeric(d$nlcd < d$imp_floor_px)

# The analysis sample: parcels built on or before the product epoch.
m <- d[!is.na(d$yr) & d$yr <= 2019, ]

# Local planar coordinates in km for the spatial estimator. Equirectangular,
# tuned to the sample latitude: EPSG:5070 Albers is equal-area and distorts
# distance, which is the wrong property for a distance-decay kernel.
lat0  <- mean(m$lat)
m$xk  <- (m$lon - mean(m$lon)) * 111.32 * cos(lat0 * pi / 180)
m$yk  <- (m$lat - mean(m$lat)) * 110.57

H <- c("canopy", "ac", "sqft", "slope", "n100")

# ---------------------------------------------------------------- estimation
fit <- function(df, y, xs = H) {
  X <- cbind(1, as.matrix(df[, xs, drop = FALSE]))
  Y <- as.numeric(df[[y]])
  XtXi <- solve(crossprod(X))
  b <- as.numeric(XtXi %*% crossprod(X, Y))
  list(X = X, b = b, e = Y - X %*% b, XtXi = XtXi)
}

se_hc1 <- function(f, which = 2) {
  n <- nrow(f$X); k <- ncol(f$X)
  meat <- crossprod(f$X * as.numeric(f$e)^2, f$X)
  V <- f$XtXi %*% meat %*% f$XtXi * n / (n - k)
  sqrt(diag(V))[which]
}

# Conley spatial HAC with a Bartlett kernel, grid-accelerated so only pairs
# within one cell of each other are visited. No origin choice enters: the grid
# is an accelerator, and every pair inside the cutoff is weighted by distance
# regardless of which cell it lands in.
se_conley <- function(f, xs, ys, cutoff, which = 2) {
  n <- nrow(f$X); k <- ncol(f$X)
  Xe <- f$X * as.numeric(f$e)
  gx <- floor(xs / cutoff); gy <- floor(ys / cutoff)
  key <- paste(gx, gy, sep = "_")
  idx <- split(seq_len(n), key)
  # Chunked, for the same measured reason as the Python implementation.
  # Settlement here is clustered: five of 47 occupied 5 km cells hold half the
  # parcels, so the busiest cell produced a single outer() of roughly
  # 11,000 x 11,000 doubles and this script peaked at 918 MB resident. That is
  # enough to be killed on a modest laptop, which defeats the point of shipping
  # an independent implementation a reviewer is meant to be able to run.
  #
  # Rows of I are processed in blocks sized so no intermediate exceeds BLOCK
  # pairs. Every pair inside the cutoff is still visited once and weighted by
  # the same kernel; only the order of summation changes.
  BLOCK <- 4e6
  meat <- matrix(0, k, k)
  for (nm in names(idx)) {
    I <- idx[[nm]]
    ab <- as.integer(strsplit(nm, "_", fixed = TRUE)[[1]])
    for (da in -1:1) for (db in -1:1) {
      J <- idx[[paste(ab[1] + da, ab[2] + db, sep = "_")]]
      if (is.null(J)) next
      step <- max(1, floor(BLOCK / length(J)))
      for (b in seq(1, length(I), by = step)) {
        Ib <- I[b:min(b + step - 1, length(I))]
        dist <- sqrt(outer(xs[Ib], xs[J], "-")^2 + outer(ys[Ib], ys[J], "-")^2)
        w <- pmax(1 - dist / cutoff, 0)
        meat <- meat + crossprod(Xe[Ib, , drop = FALSE], w %*% Xe[J, , drop = FALSE])
      }
    }
  }
  V <- f$XtXi %*% meat %*% f$XtXi * n / (n - k)
  sqrt(diag(V))[which]
}

# ---------------------------------------------------------------- the checks
FAIL <- 0L
check <- function(label, printed, computed, tol) {
  ok <- abs(printed - computed) <= tol
  if (!ok) FAIL <<- FAIL + 1L
  cat(sprintf("   %-4s %-46s manuscript %-12s computed %s\n",
              if (ok) "ok" else "FAIL", label,
              format(printed), format(round(computed, 4))))
}

cat("SAMPLE\n")
check("analysis sample, parcels", 21931, nrow(m), 0)
check("full frame, parcels", 24088, nrow(d), 0)

cat("\nTABLE 1  measured NLCD impervious percentage\n")
f1 <- fit(m, "nlcd")
check("canopy coefficient", -21.8958, f1$b[2], 0.005)
# Table 1 reports HC1 and Conley at 1, 2 and 5 km, and its t column is the 5 km
# one. Two expected values were wrong on the first run of this script: -11.0 was
# assumed to be the HC1 t when HC1 is -51.4, and was then also assumed to be the
# Conley t when Conley at 5 km is -9.7. Both R and Python agree on both figures;
# it was the README that carried -11.0, and it has since been corrected.
check("HC1 t", -51.4, f1$b[2] / se_hc1(f1), 0.06)
check("Conley t, 5 km cutoff", -9.7, f1$b[2] / se_conley(f1, m$xk, m$yk, 5), 0.06)

cat("\nTABLE 1  detection failure, the product reports less than the bound\n")
f2 <- fit(m, "below")
check("canopy coefficient", 0.3119, f2$b[2], 0.0006)
check("breach rate, percent", 58.8, 100 * mean(m$below), 0.06)

cat("\nSECTION 2.2  the bound itself\n")
check("mean bound, percent of cell", 25.1, mean(m$imp_floor_px), 0.06)
# The 35.2 percent of parcels whose roof is provably inside its own cell is NOT
# derivable from this CSV: it needs the centroid-to-cell-edge distances in
# parcel_edge_exact.csv, compared against half the roof side. The first version
# of this script invented a formula from the columns to hand and got 66.7
# percent, which is a different quantity entirely. Left out rather than
# approximated: an independent check that quietly redefines the thing it checks
# is worse than no check.
cat("\nTABLE 3  share of parcels where each product reports less than the bound\n")
for (p in list(c("below_wc", "ESA WorldCover", "75.9"),
               c("below",    "NLCD impervious", "58.8"),
               c("below_dw", "Dynamic World",   "21.6"),
               c("below_ghsl", "GHSL built surface", "72.2"))) {
  col <- p[1]
  if (!col %in% names(m)) next
  # every breach indicator is rederived here from the TRUNCATED bound, exactly
  # as the paper defines it, rather than read from the released column
  src <- switch(col, below = m$nlcd, below_dw = m$dw, below_wc = m$wc,
                below_ghsl = m$ghsl)
  check(sprintf("%s below the bound, percent", p[2]), as.numeric(p[3]),
        100 * mean(src < m$imp_floor_px), 0.06)
}

cat("\nSECTION 2.4  the effect over the observed interquartile range\n")
q <- quantile(m$canopy, c(0.25, 0.75))
check("canopy first quartile", 0.19, q[1], 0.005)
check("canopy third quartile", 0.68, q[2], 0.005)
check("impervious effect over the IQR, points", -10.6,
      f1$b[2] * (q[2] - q[1]), 0.05)

cat("\n")
if (FAIL > 0) {
  cat(sprintf("%d VALUE(S) DISAGREE WITH THE MANUSCRIPT.\n", FAIL))
  quit(status = 1)
}
cat("All headline values reproduce in R, independently of the Python harness.\n")
