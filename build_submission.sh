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
# Build the two archives the author uploads: the submission and the figures.
# Run from this directory.
#
# WHY THIS SCRIPT EXISTS
# ----------------------
# The reproduction package has had a gated builder from the start. These two did
# not. They were assembled by hand, from a staging directory that no longer
# exists, and each carried a hand-written README quoting numbers a reader would
# trust: the reproduction package's file count, the assertion count, every
# figure's pixel dimensions and dpi. Nothing checked any of them, and one was
# wrong: the submission README said the package holds 65 files when it holds 64.
#
# Two things now stop that recurring. This script rebuilds both archives from the
# working tree, so what ships is never a copy of a copy; and make_tables.py's
# archive gate reads the built archives back and checks their prose against the
# artefacts. The gate is the enforcement. This is the reproducibility.
#
# The READMEs are authored files in this directory, README_submission.txt and
# README_figures.txt, not generated prose. Numbers in them are checked, not
# substituted, because prose written to be read by a person under submission
# pressure is worth writing by hand.
set -euo pipefail
cd "$(dirname "$0")"

SUB=canopy_bias_submission.zip
FIG=canopy_bias_figures.zip
MS=canopy_bias_manuscript_GIScienceRS

# Submission-side figure names, and the working-tree file each is a copy of. The
# names are the manuscript's figure numbers; the working-tree names are the
# figure scripts' outputs. make_tables.py asserts that this mapping matches the
# captions, so a renumbered figure fails there rather than shipping mislabelled.
declare -A FIGURES=(
  [Figure1.tif]=figure_studyarea.tif
  [Figure1.pdf]=figure_studyarea.pdf
  [Figure2.tif]=figure_schematic.tif
  [Figure2.pdf]=figure_schematic.pdf
  [Figure3.tif]=figure_matched_parcels.tif
  [Figure3.pdf]=figure_matched_parcels.pdf
  [Figure4.tif]=figure_divergence.tif
  [Figure4.pdf]=figure_divergence.pdf
  [GraphicalAbstract1.png]=GraphicalAbstract1.png
)

echo "== gates =="
python3 make_tables.py   > /dev/null || { echo "numeric harness failed"; exit 1; }
python3 check_layout.py  > /dev/null || { echo "layout checks failed"; exit 1; }
python3 check_colours.py > /dev/null || { echo "colour checks failed"; exit 1; }
echo "   all three pass"

# The submission gate is REPORTED, not enforced. It fails while the manuscript
# still carries the DOI placeholder, and the archive has to be assemblable before
# the deposit exists, which is the whole point of the README's first section.
# Enforcing it here would mean the author could not build the thing that tells
# him what is left to do.
if python3 check_layout.py --submission > /dev/null 2>&1; then
  echo "   submission gate clean: no placeholders left"
else
  echo "   NOTE  check_layout.py --submission still exits 1. Run it and read the"
  echo "         placeholder it names. Do not upload until it exits 0."
fi

echo "== checking inputs exist =="
missing=0
for f in "$MS.docx" "$MS.pdf" COVER_LETTER.docx COVER_LETTER.pdf \
         README_submission.txt README_figures.txt "${FIGURES[@]}"; do
  [[ -e $f ]] || { echo "   MISSING $f"; missing=1; }
done
[[ $missing -eq 0 ]] || { echo "refusing to build an incomplete submission"; exit 1; }

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

# ---------------------------------------------------------------- figures zip
mkdir -p "$STAGE/fig"
for k in "${!FIGURES[@]}"; do cp -p "${FIGURES[$k]}" "$STAGE/fig/$k"; done
# The figures archive calls it README.txt; inside the submission archive the same
# file is README_figures.txt, so a reader who opens the 03_Figures folder is not
# looking at a file called README next to three other READMEs. One source, two
# names. make_tables.py checks the two copies are identical.
cp -p README_figures.txt "$STAGE/fig/README.txt"
rm -f "$FIG"
( cd "$STAGE/fig" && zip -qX "$OLDPWD/$FIG" . -r )

# ------------------------------------------------------------- submission zip
# Numbered folders, one file per slot, in the order a submission form asks. The
# reference renderings sit in a folder whose name says not to upload them,
# because the way to end up with two versions of record is to upload the PDF as
# the manuscript.
mkdir -p "$STAGE/sub"/{01_Manuscript,02_Cover_letter,03_Figures,Reference_renderings_do_not_upload}
cp -p "$MS.docx"          "$STAGE/sub/01_Manuscript/"
cp -p COVER_LETTER.docx   "$STAGE/sub/02_Cover_letter/"
for k in "${!FIGURES[@]}"; do cp -p "${FIGURES[$k]}" "$STAGE/sub/03_Figures/$k"; done
cp -p README_figures.txt  "$STAGE/sub/03_Figures/README_figures.txt"
cp -p "$MS.pdf" COVER_LETTER.pdf "$STAGE/sub/Reference_renderings_do_not_upload/"
cp -p README_submission.txt "$STAGE/sub/"
rm -f "$SUB"
( cd "$STAGE/sub" && zip -qX "$OLDPWD/$SUB" . -r )

count() {
  python3 -c "
import sys, zipfile
print(sum(1 for i in zipfile.ZipFile(sys.argv[1]).infolist() if not i.is_dir()))
" "$1"
}
echo "== $FIG built, $(count "$FIG") files, $(du -h "$FIG" | cut -f1) =="
echo "== $SUB built, $(count "$SUB") files, $(du -h "$SUB" | cut -f1) =="

# Rerun the harness so the archive gate reads what was just written. Building an
# archive and not checking it is how the wrong file count shipped.
echo "== archive gate =="
# Match on the gate's SUBJECTS, not on its success wording. The first version of
# this grepped for "submission archive", which is only in the line the gate prints
# when everything agrees; a real disagreement prints a different line naming the
# file, so the build reported "the archive gate produced no line" and blamed the
# harness for working correctly. Any archive-gate line is captured now, and a FAIL
# among them fails the build.
gate=$(python3 make_tables.py --quiet 2>&1 |
       grep -iE 'submission archive|README_submission|README_figures|Figure[0-9]\.(tif|pdf)|GraphicalAbstract1' || true)
if [[ -z $gate ]]; then
  echo "   the archive gate produced no line at all; check make_tables.py"
  exit 1
fi
echo "$gate"
if grep -q 'FAIL' <<<"$gate"; then
  echo "   the archives disagree with the package or the working tree, above."
  echo "   Fix what the line names, then run this script again."
  exit 1
fi
