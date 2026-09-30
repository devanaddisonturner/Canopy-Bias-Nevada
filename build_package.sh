#!/usr/bin/env bash
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
# Build the reproduction package. Run from this directory.
#
# The package is built from an explicit list rather than by globbing, so a
# stray working file cannot slip into a public release and a file that should
# be there cannot silently go missing. The build refuses to run unless all
# three gates pass, so a released zip is always one that verifies.
set -euo pipefail
cd "$(dirname "$0")"

ZIP=canopy_bias_reproduction_package.zip

echo "== gates =="
python3 make_tables.py   > /dev/null || { echo "numeric harness failed"; exit 1; }
python3 check_layout.py  > /dev/null || { echo "layout checks failed"; exit 1; }
python3 check_colours.py > /dev/null || { echo "colour checks failed"; exit 1; }
echo "   all three pass"

FILES=(
  README.md
  SUBMISSION_CHECKLIST.md
  LICENSE
  LICENSE_DECISION.md
  GITHUB_AND_ZENODO.md
  .zenodo.json
  CHECKSUMS.sha256
  .github/workflows/verify.yml
  requirements.txt
  CITATION.cff
  .gitignore
  REFERENCES_VERIFIED.md
  canopy_bias_pipeline.md
  canopy_bias_results.md

  run_full_analysis_browser.js
  canopy_bias_extraction.js
  gee_matched_parcel_panels.js
  figure_boundaries_gee.js
  signal_check_v3.js
  nlcd_vs_ghsl_check.js
  verify_support.js
  analyze_canopy_bias.py
  runoff_consequence.py
  conley.py
  verify_in_r.R

  run_all.py
  test_harness.py
  make_tables.py
  make_parcel_edge_exact.py
  check_layout.py
  check_colours.py
  strip_provenance.py
  build_package.sh
  build_submission.sh
  README_submission.txt
  README_figures.txt

  make_figure_matched_parcels.py
  make_figure_studyarea.py
  make_figure_schematic.py
  make_figure_divergence.py
  make_graphical_abstract.py
  build_manuscript.js

  nevada_canopy_bias_rowlevel.csv
  parcel_edge_exact.csv
  parcel_extras.csv
  ca_county_scan.csv
  ms_footprint_validation.csv
  nlcd_vs_ghsl_check.csv
  figure_boundaries.json

  # All four manuscript figures ship the same three formats as of 29 September
  # 2026. Figures 1 and 3 had no PDF until then, which made the set look like a
  # judgement about those figures when it was just an omission. What the PDFs
  # ARE still differs and is documented in each script: Figures 1, 2 and 4 are
  # vector (Figure 1 apart from a 648x39 colourbar strip), Figure 3 carries six
  # 633x633 rasters. make_tables.py asserts the format set is uniform.
  figure_studyarea.png     figure_studyarea.tif     figure_studyarea.pdf
  figure_schematic.png     figure_schematic.tif     figure_schematic.pdf
  figure_matched_parcels.png figure_matched_parcels.tif figure_matched_parcels.pdf
  figure_divergence.png    figure_divergence.tif    figure_divergence.pdf
  GraphicalAbstract1.png

  canopy_bias_manuscript_GIScienceRS.docx
  canopy_bias_manuscript_GIScienceRS.pdf
)

echo "== checking every listed file exists =="
missing=0
for f in "${FILES[@]}"; do
  [[ -e $f ]] || { echo "   MISSING $f"; missing=1; }
done
[[ $missing -eq 0 ]] || { echo "refusing to build an incomplete package"; exit 1; }

rm -f "$ZIP"
# -X drops extra file attributes so the zip is reproducible across machines.
# matched_parcel_panels holds the six Earth Engine panel exports that make_figure_matched_parcels.py
# composes. A nested matched_parcel_panels/figure_panels/ once shipped alongside it: a
# second copy, pixel for pixel identical, that nothing read. It is excluded.
zip -qXr "$ZIP" "${FILES[@]}" matched_parcel_panels -x 'matched_parcel_panels/figure_panels/*'

# Count FILES, not zip entries. The summary line of `unzip -l` says "65 files"
# for this archive because it counts the matched_parcel_panels/ DIRECTORY entry
# as one of them. The package holds 64 files. That off-by-one was read off this
# line and copied into the submission README, where nothing checked it until the
# archive gate in make_tables.py did. Python counts here because it can tell a
# directory entry from a file, which the `unzip -l` summary cannot.
n=$(python3 -c "
import sys, zipfile
print(sum(1 for i in zipfile.ZipFile(sys.argv[1]).infolist() if not i.is_dir()))
" "$ZIP")
echo "== $ZIP built, $n files, $(du -h "$ZIP" | cut -f1) =="
unzip -l "$ZIP" | grep -c 'figure_panels/' >/dev/null && \
  { echo "   FAIL the duplicate panel directory is still in the zip"; exit 1; } || true
echo "   duplicate panel directory excluded"
