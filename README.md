# Canopy bias in built-surface products: reproduction package

Nevada County, California. Everything needed to reproduce the results, plus the
record of what was tried and rejected along the way.

Last updated 2026-09-29.

## Start here

```
pip install -r requirements.txt
python3 run_all.py                 # everything, one verdict, about 70 seconds
```

Or, for the numbers alone, `python3 make_tables.py --quiet`, about 62 seconds.
Both are wall clock on a clean unzip, each timed more than once rather than
measured a single time, and both vary by a few percent between runs, so they are
stated as approximate rather than to the second.

`--quiet` is the shorter option, not the faster one. The full run costs the same
62 seconds, because the time goes into the spatial-HAC computation rather than
into printing. What the flag changes is 710 lines of output down to 171.

`run_all.py` is the single entry point and takes no arguments, so opening it in
IDLE and pressing F5 does the same thing as a terminal. It runs the numeric
harness, the layout checks, the colour checks, an independent reimplementation in
base R and a self-test of the harness itself, and prints one verdict. Missing
poppler or R are reported and skipped rather than failing.

If you want to read rather than run, the three files that matter are
`make_tables.py` for what is asserted and against what,
`run_full_analysis_browser.js` for how the released data was produced, and
`nevada_canopy_bias_rowlevel.csv` whose columns are documented below.

A full `make_tables.py` run prints 710 lines from a clean unzip, 522 of them
confirmations. Use `--quiet` for 171. Measured, not estimated.

## Requirements

```
pip install -r requirements.txt
```

Python 3.11 or newer. The floor is pandas': pandas 3.0 declares
`Requires-Python >=3.11`, so 3.10 cannot install `requirements.txt` at all.
Tested on **3.11, 3.12 and 3.13**, all reaching the same 522 assertions, and CI
runs all three on every push. 3.11 produced the released results.

Versions are pinned to the ones that produced the released results. pandas has
changed `qcut` and groupby behaviour across major versions and several
assertions run to four decimal places, so an unpinned environment is not a
reproducible one. SciPy and statsmodels are optional: the harness skips two
checks without them and the assertion count falls from 522 to 517, which it
reports rather than hides.

Rebuilding the manuscript `.docx` additionally needs Node (built with v22.22.2)
and the `docx` npm package. Verifying the numbers does not.

## What reproduces offline, and what does not

Worth being plain about, because "reproducible" is often claimed more broadly
than it is true.

**Everything the manuscript prints reproduces offline from the released CSVs**,
with no account anywhere and no network. That is the whole of the numeric
harness, the four tables, the four figures, the graphical abstract and the
layout and colour gates:

```
python3 run_all.py         # everything below, with one verdict
```

or individually:

```
python3 make_tables.py     # 522 assertions against the released data
python3 check_layout.py    # the rendered manuscript's typography and pagination
python3 check_colours.py   # dichromacy and greyscale legibility of every figure
Rscript  verify_in_r.R     # the headline results, reimplemented in R
python3 test_harness.py    # whether each lint fires on the defect it catches
```

The harness also checks the four figures **inside** the `.docx` against the
figure files on disk, pixel by pixel, so a regenerated figure that never made it
into a rebuilt manuscript is caught. That comparison has to be by pixels rather
than bytes, and the reason is worth stating, because it is the reason to expect
`cmp` to disagree where the images agree.

Image writers can attach a content-credentials manifest (C2PA, a JUMBF box) to a
file they produce. Such a manifest carries an identifier minted when the file is
written, so two runs that draw exactly the same picture still produce different
bytes, and embedding strips the manifest, so the copy inside a document differs
from the file on disk. No image shipped here carries one, and `make_tables.py`
checks all fifteen on every run. It used to check nine. The six it could not see
were the Earth Engine panel exports under `matched_parcel_panels/`, which
`build_package.sh` ships as a directory rather than as named files, and all six
carried a manifest asserting that Claude had provided the file and may have
created it. They are exports of public NAIP, NLCD and Meta canopy imagery, so
that was a false claim about their origin, bound for a public deposit. The
manifests were stripped on 29 September 2026; the panels decode pixel-identical
without them and Figure 3 rebuilds byte-identical from the stripped panels, which
is why the six hashes in `CHECKSUMS.sha256` changed and why that file now records
the reason. If you regenerate them and byte-compare
against a copy taken from somewhere that does attach one, expect a fixed
difference of about 5,770 bytes per PNG and identical pixels. **The reproducibility
claim for figures is pixel identity, not byte identity**, and the harness asserts
the claim it can keep.

**If your environment does not match the pins, the harness says so first.**
Before printing a single number it compares the installed numpy and pandas
against `requirements.txt` and, on a mismatch, explains in a banner that some
values will not reproduce and why. That is measured: under pandas 2.2.3 rather
than the pinned 3.0.2, `qcut` resolves a tie differently, one parcel moves
between deciles, the smallest decile becomes 2,188 instead of 2,189, and five
values shift with it. Without the banner those read as defects in the
manuscript, which is the wrong conclusion to hand a reader.

**What a full verification costs:** about 70 seconds and under half a gigabyte.
`make_tables.py` peaks at 450 MB and `verify_in_r.R` at 450 MB, measured in
isolation. The harness figure was 353 MB when it made 376 assertions and has risen
with the checks added since, so the headroom under 512 MB is now thinner than it
reads; a machine that has to page will feel this step. Both
Conley spatial HAC implementations are chunked, because unchunked they built one
dense distance block per pair of neighbouring grid cells and this frame is
clustered: five of 47 occupied 5 km cells hold half the parcels, so the busiest
cell alone produced an array of roughly 11,000 by 11,000 and peaked near 950 MB.
That is enough to be killed on a modest laptop, and it did kill one verification
run here. Chunking changes the order of summation and nothing else; the three
implementations still agree to 1e-9.

All five figure scripts regenerate their images **pixel for pixel**, verified by
running all five and comparing, and CI re-runs them on every push so a library
upgrade that moves a pixel is caught here rather than in someone else's reuse.
The harness also holds the workflow to the shipped file list, so a figure or
verification script added later cannot quietly fall outside CI while the step
that names it keeps its name.

`test_harness.py` is the one that tests the tester. It reintroduces, into a
temporary copy, the exact defect each lint was written for and requires the lint
to fail. This package has shipped three checks that printed "ok" while looking
at nothing, so a lint is not trusted here until it has been seen to fire. Its
first run found `first_person_lint` unable to see "We" at the start of a
sentence.

`verify_in_r.R` is base R with no packages to install, and it is an independent
reimplementation rather than a translation: it rederives the analysis sample,
the truncated bound, every breach indicator and the Conley spatial HAC from the
paper's definitions. Writing it found four stale t-values in this README's own
headline paragraph, which is what a second implementation is for.

`run_all.py` is the file to open in IDLE: File, Open, then Run Module or F5. It
takes no arguments, reports what it skipped and why, and exits 0 when everything
that could run passed. On a machine without poppler or R it skips those two
steps rather than failing, because a missing tool is not a defect in the package.

All the scripts run from **any working directory**, so IDLE's Run Module, a
double-click and `python3 /full/path/to/make_tables.py` all work; each resolves
its inputs relative to its own file. The three Python gates also degrade with a
clear message rather than a traceback when poppler is absent, which is the usual
case on Windows.

All three also run on every push through `.github/workflows/verify.yml`, and
`make_tables.py` verifies the released data against `CHECKSUMS.sha256` before
trusting it.

**Re-extraction does not.** Building the CSVs from source needs a Google Earth
Engine account and the county's ArcGIS REST service, and it is the one step a
reader cannot repeat unaided: `canopy_bias_extraction.js`,
`run_full_analysis_browser.js`, `gee_matched_parcel_panels.js`,
`figure_boundaries_gee.js` and `verify_support.js` are all Earth Engine Code
Editor scripts. They are included so the extraction can be read and audited, not
because it can be re-run from this archive. The released CSVs are their output.

## The finding

For 21,931 assessor-verified parcels each carrying a recorded dwelling, going from bare ground to full
tree canopy is associated with **18 to 22 percentage points less** measured NLCD
impervious surface (−21.90, Conley t = −9.7 unadjusted; −18.13, t = −13.2 net
of the nighttime-lights masking step), and raises the probability that NLCD
reports **less impervious surface than the recorded buildings physically
occupy** by **26 to 31 percentage points** (t = +7.7 to +8.9). All t-values are
Conley spatial HAC at a 5 km cutoff, which is the conservative choice and the
one Table 1 reports.

The range is not imprecision. NLCD's impervious layer is produced with a
nighttime-lights mask that deletes low-density impervious surface outside urban
centres, and canopy suppresses upward light emission as well as reflected
daylight, so that layer may be a mediator of the canopy effect rather than a
confounder. Lower bound treats it as a confounder; upper bound as a mediator.

It rises with canopy within every neighbour-density quartile, though not monotonically in the densest, unchanged when
restricted to paved access, and robust to how the physical floor is defined.

In a **negative control** of houses built after the NLCD epoch, the effect is
−2.45 (t = −1.37) against −21.90 in the main sample, an 87 percent reduction
not distinguishable from zero. Use that continuous outcome for the placebo. The
binary below-floor outcome sits near its ceiling in the post-2019 group and is
mechanically pushed toward a null, so its −0.0001 coefficient should not be
quoted as evidence.

## Files

### The Earth Engine scripts: where each runs, and what is checked

Eight `.js` files ship and they do not all go in the same place, which is worth
knowing before pasting one into the wrong pane and watching it fail.

**Earth Engine Code Editor** — paste into the script pane at
code.earthengine.google.com and click Run. These are the ones that can be saved as
Earth Engine script files in the usual way.

- `canopy_bias_extraction.js`, then press RUN on each queued task in the Tasks tab
- `signal_check_v3.js`
- `nlcd_vs_ghsl_check.js`
- `verify_support.js`

**Browser developer console** — open the Code Editor, press F12, paste into the
console, press Enter. These reach the Nevada County ArcGIS service as well as Earth
Engine, which the Code Editor sandbox cannot do, so they will not run in the script
pane and there is nothing to save there.

- `run_full_analysis_browser.js`
- `gee_matched_parcel_panels.js`
- `figure_boundaries_gee.js`

**What this package verifies about them, and what it does not.** An Earth Engine
script needs the Earth Engine runtime and an authenticated account, so the harness
has never executed one and cannot. What it does check: every shipped `.js` parses,
under `node --check`, which is syntax and no more; `canopy_bias_extraction.js`
states the same parcel-service record count as the manuscript and the pipeline
document; and every script named in a shipped script's comments is either in the
package or declared absent with a reason. What it does not check is that any of them
still returns what it returned when it was run. The released CSVs are the record of
that, and `CHECKSUMS.sha256` pins them.

**These files are the authority; a copy saved in a Code Editor is not.** Edit a
script inside Earth Engine and nothing here can see it, and the package will go on
describing the version it holds.

### Run these

| File | What it does |
|---|---|
| `run_full_analysis_browser.js` | **Start here.** Complete pipeline from nothing to the row-level CSV. Paste into the **browser developer console** (F12) at code.earthengine.google.com, not the script pane. About 12 minutes |
| `analyze_canopy_bias.py` | Every reported number, from the CSV. `python3 analyze_canopy_bias.py nevada_canopy_bias_rowlevel.csv` |
| `runoff_consequence.py` | What the measurement error costs a downstream user. NRCS TR-55 curve number and runoff equation |
| `conley.py` | Grid-accelerated Conley spatial HAC, as a standalone reference implementation. Nothing imports it: `analyze_canopy_bias.py` and `make_tables.py` each carry their own. The three are verified to agree to 1e-9 on identical inputs by `conley_implementations_agree()` in the harness, so the duplication cannot drift |

### Manuscript tables and figure

Every number typeset in the manuscript is regenerated and asserted against the
data by one script. If the manuscript and the data ever diverge, it exits
non-zero and names the offending value.

| File | What it does |
|---|---|
| `make_tables.py` | **Regenerates all four manuscript tables, the Figure 3 parcel selection, the Figure 4 series, the footprint identity and the block-origin sensitivity, then asserts each against the value the manuscript prints. 522 assertions, or 517 without SciPy and statsmodels.** `python3 make_tables.py nevada_canopy_bias_rowlevel.csv [--csv-out DIR]` |
| `gee_matched_parcel_panels.js` | The six panels of Figure 3. Paste into the browser console at code.earthengine.google.com; returns `getThumbURL` links for NAIP (24 July 2020), Meta and WRI canopy height, and NLCD impervious at both parcels |
| `make_figure_matched_parcels.py` | Composes those six panels into Figure 3 at 300 dpi, with the true EPSG:5070 cell footprints, scale bars and colour bars. Writes PNG and LZW TIFF |
| `make_figure_studyarea.py` | Figure 1. The county, the 21,931 parcels coloured by canopy, a California inset and the two illustrated parcels. Boundaries from `figure_boundaries.json` |
| `make_figure_schematic.py` | Figure 2. How the bound is built: floor area ÷ storeys **plus attached garage**, summed into the 30 m cell. Asserts the footprint identity against the data |
| `make_figure_divergence.py` | Figure 4. The bound against measured impervious by canopy decile, and the two failure rates. This figure replaced a table |
| `verify_support.js` | Paste into the Earth Engine Code Editor to settle two open questions without re-exporting anything: whether the 30 m cell the bound is summed over is the same cell NLCD reports, and whether the released covariates are 20 m disc means or values on the 30 m grid. It only prints |
| `figure_boundaries.json` | Nevada County and California outlines, TIGER/2018 via Earth Engine; see `figure_boundaries_gee.js` |
| `make_graphical_abstract.py` | The 525 px graphical abstract, submitted as a separate file. Its gap and sample size are computed from the released data, so they cannot drift from the manuscript |
| `build_manuscript.js` | Builds the submission .docx: text, four tables, four embedded figures, four equations, references. `node build_manuscript.js`. Requires the `docx` npm package |

### The three gates

Each one exits non-zero and names what failed, and each was proved to fire on a
deliberately broken copy before it was accepted.

| File | What it catches |
|---|---|
| `make_tables.py` | Numbers, prose and captions that disagree with the data |
| `check_layout.py` | What only the rendered PDF and DOCX show: a caption split from its figure, an uncentred table header, roman Greek variables, an unbolded cross-reference, wrong document metadata, a stranded heading, a widow, a near-empty page |
| `check_colours.py` | Colours a reader cannot tell apart. Simulates protanopia, deuteranopia and tritanopia by the Vienot, Brettel and Mollon (1999) LMS method, requires a worst-case separation of 40 between any two colours drawn in the same panel, requires 3:1 luminance contrast for a marker over a colour ramp or a white casing instead, and then confirms in the rendered pixels that the casing is really there |

| `build_package.sh` | Builds the release zip from an explicit file list, and refuses to build unless all three gates pass |
| `strip_provenance.py` | Removes an embedded C2PA content-credentials manifest from a shipped image, in place, without re-encoding. It exists for the six Earth Engine panel exports under `matched_parcel_panels/`, which are inputs that no script regenerates, so the usual fix of rerunning a figure script does not apply to them. It decodes both versions and refuses to write unless the pixels, mode and size are identical, because a manifest strip that changed a pixel would be a silent edit to released data. Report-only by default; `--write` to act |
| `build_submission.sh` | Builds the two archives the author uploads, `canopy_bias_submission.zip` and `canopy_bias_figures.zip`, from this working tree, behind the same three gates. Both were assembled by hand until 29 September 2026, which is how their READMEs came to state a file count nothing checked, and state it wrongly |
| `README_submission.txt` | The prose that ships at the root of the submission archive: what to upload into which slot, what is deliberately absent, and what has to be settled before upload. Authored here rather than generated, and checked rather than substituted: `make_tables.py` reads the built archive back and compares its file count, assertion counts and figure dimensions against the artefacts |
| `README_figures.txt` | The prose that ships with the figures, under that name inside the submission archive's `03_Figures/` and under the plain name README.txt, unbackticked here because no such file is in this package, in the figures archive. States each figure's pixel dimensions and dpi, every one of which is read back out of the shipped image by the archive gate, and why these must not be converted to EPS |

The division of labour matters. `make_tables.py` is the authority for the
numbers; `build_manuscript.js` only typesets them. The table values are literals
in the builder, which is why the assertion script exists.

### Data

| File | Contents |
|---|---|
| `nevada_canopy_bias_rowlevel.csv` | **24,088 parcels**, 39 columns. The complete qualifying census, not a sample. `imp_floor_px` and `floorA` are the **untruncated** bounds, because the truncation diagnostics need the raw values; the 100 percent ceiling of Equation 2 is applied to the breach indicators derived from them |
| `parcel_edge_exact.csv` | 24,088 rows. Distance from each parcel centroid to the nearest 30 m cell edge, with the EPSG:5070 cell indices, computed from full-precision assessor centroids. Needed by the straddle and centroid-assignment checks |
| `parcel_extras.csv` | 24,088 rows. Recorded porch, guest-house, vehicle, unit-count and bedroom fields from the assessor record. Needed by the frame-composition and porch checks |
| `ca_county_scan.csv` | 41-county California canopy-loss scan, from the original research question |
| `nlcd_vs_ghsl_check.csv` | 57-county NLCD versus GHSL comparison. See the warning below |

The breach indicators in the released file (`below`, `belowA`, `below_dw`,
`below_wc`, `below_ghsl`) were once written before the 100 percent ceiling was
applied. Analysing the file directly then gave WorldCover failing on 76.3 per
cent of parcels against the 75.9 the paper prints, because 104 cells whose raw
bound exceeds a full cell were counted as breaches. No published number was
affected, since `load()` re-derives every one of these columns from the
truncated bound, but the file itself now matches the paper and
`released_data_consistency()` asserts that it does.

The two `parcel_*.csv` files were once omitted from this package. The harness
then ran 293 of its assertions instead of all of them, skipped the rest with a
one-line note, and still printed its success message. It now records every
skipped group and **exits non-zero** unless `--allow-missing` is passed, so a
partial verification can no longer be mistaken for a complete one.

### Documentation

| File | Contents |
|---|---|
| `canopy_bias_results.md` | All results with limitations stated |
| `canopy_bias_pipeline.md` | Design rationale, diagnostics, dead ends |

### Rendered outputs

These are what the scripts above produce. They are in the package so a reviewer
can compare the built artefacts against a fresh run, not because anything needs
them as input.

| File | What it is |
|---|---|
| `canopy_bias_manuscript_GIScienceRS.docx`, `.pdf` | The manuscript, 23 pages, as submitted |
| `figure_studyarea.png`, `.tif`, `.pdf` | Figure 1, from `make_figure_studyarea.py`, at 600 dpi with a vector PDF. It shipped at 300 dpi with no PDF until 29 September 2026, described as photographic; everything in it is drawn except the colourbar, and its PDF holds exactly one raster object, that 648 x 39 colourbar strip at 300 dpi |
| `figure_schematic.png`, `.tif`, `.pdf` | Figure 2, from `make_figure_schematic.py`, at 600 dpi with a fully vector PDF |
| `figure_matched_parcels.png`, `.tif`, `.pdf` | Figure 3, from `make_figure_matched_parcels.py`, at 300 dpi. That is the ceiling, not a concession: each panel prints 2.107 in wide from a 633 px Earth Engine export, which is 300.5 dpi, so 600 would upsample. Its PDF carries those six exports as rasters |
| `figure_divergence.png`, `.tif`, `.pdf` | Figure 4, from `make_figure_divergence.py`, at 600 dpi with a fully vector PDF |
| `GraphicalAbstract1.png` | The graphical abstract, 525 x 388 px, from `make_graphical_abstract.py` |
| `SUBMISSION_CHECKLIST.md` | Journal requirements, checked, with the decisions taken |
| `REFERENCES_VERIFIED.md` | Every reference and every quoted literature figure, checked against its source |

No EPS is supplied, deliberately: matplotlib's PostScript backend renders
transparency opaque, which would turn Figure 4's shaded band into a solid block
over the curves. Use the PDF or the 600 dpi raster.

### Superseded, kept for the record

`canopy_bias_extraction.js` is in this package and is superseded. It was the
asset-upload route, written before it became clear that the whole census could be
pulled and sampled directly in the browser. `run_full_analysis_browser.js`
replaces it and is the file to start from; the two differ in what they extract,
so reading the older one will mislead you about the released columns. It is kept
only so the provenance of the earlier draft's numbers is traceable.

Three further scripts from the work are deliberately **not** in this package,
because nothing here depends on them and shipping them would invite exactly the
confusion above: the first-stage parcel pull that fed the asset-upload route, and
two nighttime-lights signal checks belonging to the original research question,
which closed as a null. They are described in `canopy_bias_pipeline.md`.

## Column reference for the row-level CSV

| Column | Meaning |
|---|---|
| `apn` | Assessor parcel number, unformatted and twelve digits. The county's dashed form 045-300-033, which the Figure 2 caption uses, is `045300033000` here |
| `lon`, `lat` | Parcel centroid, WGS84 |
| `ac`, `sqft`, `storeys`, `garage` | Assessor: acres, living area, storeys, garage sqft. Porch area is not here; it is a column of `parcel_extras.csv` |
| `roof_m2` | `(sqft / storeys + garage) × 0.092903`. Porch and guest house excluded to stay conservative: they add 112.5 ha, 32.0% of the counted roof, and would raise the breach rate from 58.8% to 68.2% |
| `yr`, `improve`, `use`, `road` | Year built, improvement value, use code, road surface |
| `px` | EPSG:5070 30 m NLCD pixel id |
| `pixel_roof_m2`, `n_bldg_px` | Summed roof area and building count in that pixel |
| `imp_floor_px` | **The physical floor**, percent: `100 × pixel_roof_m2 / 900` |
| `floorA` | Conservative floor with garage excluded |
| `n100`, `n250` | Built parcels within 100 m and 250 m. The density control |
| `canopy`, `canopy5`, `canopy_ht` | Canopy fraction above 2 m, above 5 m, and mean height, on the 30 m grid |
| `nlcd`, `dev` | NLCD 2019 percent impervious; developed class 21–24 as 0 or 100 |
| `dw`, `wc`, `ghsl` | Dynamic World built probability, ESA WorldCover built, GHSL built surface percent |
| `slope` | Degrees, from 3DEP 10 m |
| `elev` | Elevation in metres, 3DEP 10 m aggregated to 30 m |
| `viirs`, `dmsp` | VIIRS 2016 median radiance and DMSP 2011 stable lights, the two layers NLCD used for its masking step |
| `descr` | NLCD `impervious_descriptor`; 0 means non-impervious |
| `lc` | NLCD land cover class (41 deciduous, 42 evergreen, 43 mixed forest) |
| `below`, `belowA`, `zero` | NLCD below the floor; below the conservative floor; reports exactly zero |
| `below_dw`, `below_wc`, `below_ghsl` | Same test for the other three products |

## Verification

Every headline number was computed twice by independent implementations, once in
JavaScript in the browser and once in Python from the written CSV. They agree to
four decimal places. Both are included deliberately rather than tidying one away.

The consolidated script's `buildStack` was executed as written against 400
parcels and six bands. Maximum absolute difference from the stored dataset: **0**.

Earth Engine assumptions were tested rather than assumed:

| Check | Result |
|---|---|
| Is Meta canopy masked off-canopy, which would break every mean? | **No.** `unmask(0)` moves a paved disc from 0.04498 to 0.04498 |
| Does `ee.Terrain.slope` handle 3DEP's geographic projection? | **Yes.** A steep canyon returns p5 3.2, p50 20.2, p95 38.2, p99 42.7 degrees |
| GHSL units | m² per 100 m cell, 0 to 10000, so divide by 100 |
| EPSG:5070 conversion | Origin (96 W, 23 N) maps to (0, 0); a 10 m offset returns 10 m and lands in the adjacent 30 m cell |

## Traps, all of which were hit

- **A median composite carries no default projection.** `reduceResolution` fails on Dynamic World unless `setDefaultProjection` comes first.
- **An explicit `.reproject()` forces a county-wide output grid** and throws "Reprojection output too large" on spatially dispersed chunks.
- **Omitting `reduceResolution` entirely is also wrong.** `sampleRegions` then does nearest-neighbour and returns a binary point sample instead of a 30 m canopy fraction.
- **`reduceResolution` from 30 m to 100 m needs `maxPixels` of at least 1,069.** The default 1,024 fails.
- **`2021_REL/NLCD` contains only the 2021 image.** A 2001 filter against it returns null. Historical years live in `2019_REL`.
- **Filter image collections to bounds before `.mosaic()`.** Mosaicking all 170 global canopy tiles first will time out.
- **ArcGIS returns records in internal order, which is spatially clustered.** A naive ordered pull sampled one town, sd(lon) 0.015 against 0.4366 for the census, and inflated the canopy coefficient from −22 to −37. Take the census; do not sample.
- **`Floor1SquareFeet`, `Floor2SquareFeet`, `BasementSquareFeet` and `ImprovementsSquareFeet` are in the schema and entirely empty.** `Floor1SquareFeet` would have been the ideal footprint field.
- **Earth Engine interactive computation times out near five minutes.** Chunk at about 1,000 points.

## Dead ends, do not retry

- **VIDA_COMBINED/USA building footprints.** A 20 m disc returned 31 overlapping polygons totalling 36,000 m² against a disc area of 1,257 m². Geometrically impossible for clean footprints.
- **A near-zero-canopy control county.** Sacramento has 4 of 174 developed locations above 50 percent canopy, so it cannot test the range where the effect is strongest.
- **Canopy removal as a treatment.** Clearing is often part of development, so impervious surface genuinely increases and the design scores a true positive as an artefact.
- **A stormwater impervious-area dataset for Nevada County.** All 221 layers in the county's ArcGIS Online organisation were listed; none carries impervious area. The county is not an urbanised MS4.
- **The floor computed on a 20 m disc rather than the NLCD pixel.** Flags isolated houses regardless of canopy, because the disc and the measurement have different denominators.

## Warnings about specific files

`nlcd_vs_ghsl_check.csv` reports a 30.9 percent "missed growth" headline, which
is the unweighted mean of `pct_growth_outside_nlcd_developed` across the 57
counties and is reproducible from the file. **It is a proportional-allocation
artefact, it is not a result, and it should not be cited.** Weighting counties by
their own built growth instead of averaging them equally already drops it to 17.9
percent, which is reproducible from the file too, and a strict binary rule
collapses it further. That strict-rule figure needs the underlying GHSL and NLCD
pixels, which are not released here, so it is not recomputable from this summary
and no value for it is quoted.

Any number in older notes quoting a canopy coefficient of **−26.15 or −36.8 is
superseded**. The census value with a density control is **−21.90**.

## The rival explanation, tested

The MRLC metadata for NLCD 2019 impervious states that nighttime lights (DMSP
2011, VIIRS 2016) were imposed on existing NLCD data "to exclude low density
impervious areas outside urban and suburban centers". That is a documented
production step deleting rural impervious surface, and it correlates with canopy
at −0.298.

Controlling for it accounts for about **one sixth** of the effect and leaves the
rest, with t-statistics improving rather than degrading. See section 7 of
`canopy_bias_results.md`. Treat the headline as a range and discuss the
mediator-versus-confounder question explicitly; a reviewer who knows the product
will raise it.

## Checks that came out in the study's favour

- **The floor is conservative.** It is driven by buildings per pixel, which falls
  with canopy, so high-canopy parcels face a lower bar and fail it anyway.
  Controlling for the floor's own drivers raises the coefficient from 0.311 to
  **0.408**.
- **Elevation is not a confound.** corr(canopy, elevation) = +0.097; adding it
  moves the coefficient from −18.49 to −18.13.

## A test that is not available here

A deciduous versus evergreen contrast would separate occlusion from spectral
mixing, because leaf-off Landsat sees through deciduous canopy. Nevada County
has **50** deciduous and **67** mixed-forest parcels against 3,075 evergreen, so
the test is impossible. Choose the replication county for forest composition,
not just adjacency.

## What the error costs downstream

`runoff_consequence.py` runs the NRCS TR-55 composite curve number and runoff
equation over the parcels. Reference is `max(NLCD, floor)`, and because the
floor is roof area only, every figure is a lower bound.

At a 3-inch storm on hydrologic soil group B, an NLCD-based runoff estimate
captures **76 percent** of the reference across the sample and **60 percent** in
the top canopy decile. The error is largest on well-drained soils and for small
frequent storms, which are the ones that govern water-quality permitting rather
than flood peaks. Unaccounted volume for one such storm across the frame is
about **86 acre-feet**.

The absolute volume is modest. The point is that the error is systematic,
one-directional, concentrated in the wildland-urban interface, and invisible to
the product's own validation, so it is inherited silently by stormwater
permitting, first-flush design, TMDL allocation and WUI exposure modelling.

## Known limitations

1. **Pixel assignment is by parcel centroid.** A building is assumed to sit in the pixel containing its parcel centroid. Each parcel is therefore evaluated at a pixel that received its own full roof, which slightly overstates the floor at the point of evaluation and pushes the *level* of the below-floor rate up. Assignment error is **not** canopy-independent: larger parcels are more likely to have the building away from the centroid, and acres correlates with canopy at +0.283. An earlier version of this note asserted independence without testing it, which was wrong. Tested on the census, the gradient runs *against* the confound rather than with it: the effect is −34.06 on the smallest acreage quartile, where assignment error is smallest, against −13.93 on the largest and −21.90 pooled (results section 8). Re-running on parcel polygons, which the service does serve, would remove the noise.
2. ~~Spatial block-cluster standard errors, not Conley HAC.~~ **Resolved, then superseded.** Conley HAC computed for all three outcomes; headline holds at t = −9.7 at a 5 km cutoff. Two successive claims here were wrong: first that block clustering was the more conservative choice, then that Conley "exceeds the block SE at 1 km and 5 km". The second is ill-posed, because the block SE ranges 1.637 to 2.191 across 25 arbitrary grid origins at a 2 km block. Conley needs no origin and converges. The manuscript reports Conley only and discloses the block spread in the methods.
3. **Canopy is measured on a 30 m cell centred on the parcel**, not the exact NLCD Albers pixel. Up to half a pixel of offset.
4. **Canopy comes from an optical product.** Measurement error in the treatment attenuates toward zero, working against the finding.
5. **One county**, heavily forested Sierra foothills, possibly an extreme case. Placer is the replication site: 124,261 qualifying parcels, verified spatial spread, and a 3,600-parcel check reproduces the effect. Placer publishes **no storeys field**, so it supports the regression and the OEHHA comparison but NOT the floor test.
6. **The negative control has n = 589.** Report it on the continuous outcome (−2.45, t = −1.37). The below-floor version is near its ceiling there, with raw rates of 0.71, 0.85 and 0.87 by canopy tercile, so its null is partly mechanical. On the zero outcome it returns −0.219, t = −2.2, a sign reversal rather than a null.
7. **The floor assumes recorded structures exist as recorded.** Demolitions missing from the assessment roll would produce spurious breaches.

8. **The frame is sub-half-acre residential parcels; the estimate is not county-wide.** `GISACRES <= 0.5` is what makes the floor test meaningful. But acres correlates with canopy at +0.283, and inside the frame the continuous coefficient declines monotonically with parcel size, −34.06 in the smallest quartile to −13.93 in the largest, so on larger parcels the effect is likely smaller. The detection-failure coefficient is flat across the same quartiles at +0.32, so the effect's existence generalises within the frame even though its magnitude does not. Scope the claims to small-lot residential settlement.

## Next

2. Full Placer pull, 124,261 parcels. Verified: no storeys field, so no floor test there; and use `GIS_Acres`, not `Acres`, which is populated for only 22 percent of records.
3. Re-run on parcel polygons to remove centroid assignment noise.
4. Target *GIScience and Remote Sensing*, which published the NLCD 2019 and 2021 accuracy assessments and is the natural conversation partner.

## Data sources

- Nevada County assessor: `maps.nevadacountyca.gov/arcgis/rest/services/web_public/Open_Data_Layers_Nevada_County_1/FeatureServer/200`
- NLCD 2019: `USGS/NLCD_RELEASES/2019_REL/NLCD`
- Canopy height: `projects/meta-forest-monitoring-okw37/assets/CanopyHeight` (Meta and WRI, about 1.19 m)
- Dynamic World: `GOOGLE/DYNAMICWORLD/V1`
- ESA WorldCover: `ESA/WorldCover/v200`
- GHSL built surface: `JRC/GHSL/P2023A/GHS_BUILT_S`
- Terrain: `USGS/3DEP/10m`


## Repository and release files

These exist for the public release rather than for the analysis. None of them is
needed to reproduce a number.

| File | Purpose |
|---|---|
| `LICENSE` | MIT for the code, with the CC0 data dedication stated beneath it |
| `LICENSE_DECISION.md` | How the licence was chosen, and what it unblocks |
| `CITATION.cff` | Citation metadata. GitHub renders it as a "Cite this repository" button; the Zenodo DOI goes in once the deposit exists |
| `.zenodo.json` | Controls the Zenodo record's own metadata, so title, ORCID, keywords and licence come from this file rather than being guessed from the repository name |
| `.gitignore` | Excludes build products only. It deliberately does **not** exclude the rendered `.docx`, `.pdf`, figures or released CSVs: the harness checks the rendered documents against their sources and cannot do so if they are absent |
| `GITHUB_AND_ZENODO.md` | The exact steps from this package to a repository and a DOI |
| `.github/workflows/verify.yml` | Runs all three gates on every push, so the repository shows whether the released numbers still reproduce |

## Where each released dataset came from

The Open Materials claim is that the code behind the released data is released
with it. That is true for four of the six datasets and **not** for two, so it is
set out here rather than left to be discovered.

| Dataset | Produced by | In this package |
|---|---|---|
| `nevada_canopy_bias_rowlevel.csv` | `run_full_analysis_browser.js` | yes |
| `parcel_extras.csv` | `run_full_analysis_browser.js` | yes |
| `ca_county_scan.csv` | `signal_check_v3.js` | yes |
| `nlcd_vs_ghsl_check.csv` | `nlcd_vs_ghsl_check.js` | yes |
| `parcel_edge_exact.csv` | `make_parcel_edge_exact.py` | **script yes, input no** |
| `ms_footprint_validation.csv` | an interactive Earth Engine session, no seed recorded | **8 of 11 columns verified; sample not regenerable** |

Two different situations, and the distinction was wrong here until 29 September.

**`parcel_edge_exact.csv`: the script now ships; the input does not.**
`make_parcel_edge_exact.py` reconstructs it from the documented method. What it
needs is full-precision assessor centroids, and this release does not carry them:
the row-level CSV rounds them to four decimal places. Recomputing the cell
geometry from the released coordinates reproduces the cell indices for **84.33
percent** of parcels against **99.99 percent** from full precision, and `dedge`
to within 0.1 m for **3.20 percent**. All three figures are asserted by
`make_tables.py`, and the script refuses to run on the released CSV rather than
producing a file that is wrong for one parcel in six while looking plausible.
Full-precision centroids come from the county parcel service, which
`run_full_analysis_browser.js` pulls; so the file is reproducible from **source**
and not from this release alone. Saying "the script was not retained" understated
this, because a script alone would not have closed it.

**`ms_footprint_validation.csv`: most of it is verifiable, and now verified; the
sample cannot be regenerated.** The sample is 700 cells, 70 per canopy decile,
drawn from `projects/sat-io/open-datasets/MSBuildings/US/California`. Three
separate things were being run together under "no script", and they are different:

- **Eight of its eleven columns reproduce exactly** from the row-level CSV
  restricted to the analysis sample, plus `parcel_edge_exact.csv`: `i` and `j`
  from the edge file, `canopy`, `nlcd`, `roof` and `n` from the cell-level
  aggregation, and `dec` as the cell-level canopy decile.
  `make_tables.py::footprint_file_integrity` asserts all eight, so the file's
  join, its frame and its roof arithmetic are checked against the census rather
  than assumed. Notably, agreement is exact only on the analysis sample and falls
  to 98.3 percent on the full frame, which is itself evidence the file was built
  on the sample boundary the paper reports.
- **`allinside` reproduces for 99.7 percent** under a square-footprint
  approximation of the roof: close enough to show the column means what it says,
  not close enough to claim the original rule, so it is reported and not asserted.
- **`bound` is the raw ratio, not the truncated one.** It is `roof` over the
  900 m2 cell as a percentage, which reproduces exactly, and it is **not**
  truncated at 100: one cell of the 700 stands at 110.97 percent. Everywhere the
  paper uses the bound, Equation 2's ceiling is applied, so this column and the
  paper's bound differ on that one cell. It is inert for Section 3.6, whose ratios
  are taken against `roof` rather than `bound`, but it is a released CC0 column
  and a reuser could reasonably read it as the paper's bound, so the difference is
  asserted rather than left to be discovered.
- **`ms_m2` cannot be checked here at all.** It is the Microsoft Buildings
  footprint area and comes from Earth Engine. This is the one genuinely
  unverifiable column in the release.

**The 700 cells themselves cannot be regenerated.** Each canopy decile holds
between 1,807 and 1,813 candidate cells and 70 were drawn, and no seed was
recorded, so the specific sample is not recoverable. A reviewer who wants to
repeat this test should draw a fresh 700 by the same rule and compare the
distributions, which is a stronger form of replication than reproducing one
sample. What cannot be done is regenerating this file byte for byte, and no
script would change that.

The guidelines note that authors are accountable for disclosure accuracy, and an
Open Materials claim that quietly covered four of six would not be accurate.

`make_tables.py` holds this table too and fails if a released dataset is added
without a provenance decision, so the gap cannot silently widen.

## Licence and citation

**Code: MIT.** The extraction scripts, the analysis, the figure scripts and the
verification harness. See `LICENSE`.

**Data: CC0 1.0.** `nevada_canopy_bias_rowlevel.csv`, `parcel_edge_exact.csv`,
`parcel_extras.csv`, `ms_footprint_validation.csv`, `ca_county_scan.csv` and
`nlcd_vs_ghsl_check.csv` are dedicated to the public domain. This is the
dedication the manuscript's data availability statement commits to.

The two are stated separately on purpose. CC0 is a dedication designed for data
and is generally discouraged for software, so the code carries a software
licence instead. `LICENSE_DECISION.md` records how the choice was made.

### How to cite

The author is **Devan Cantrell Addison-Turner**, ORCID
[0000-0002-2511-3680](https://orcid.org/0000-0002-2511-3680), Department of Civil
and Environmental Engineering, Stanford University. That full form, middle name and
hyphen included, is what `CITATION.cff` and `.zenodo.json` carry, and it is what
BibTeX, schema.org and every other format that preserves given names will emit.

The APA renderings below show `D. C.` rather than the given names in full. That is
APA's own convention for initials, not a truncation in the metadata, and it is what
GitHub's "Cite this repository" widget displays when set to APA. Its BibTeX view
gives `author = {Addison-Turner, Devan Cantrell}`. `make_tables.py` checks the full
name in **every** author block in both metadata files against the manuscript byline,
so a middle name or a hyphen cannot be lost from one of them unnoticed.

**Cite the paper** if you are citing the argument, the method or any result:

> Addison-Turner, D. C. (2026). An optically independent administrative reference
> for validating built-surface products, and the tree-canopy bias it reveals.
> Manuscript prepared for submission to *GIScience & Remote Sensing*.

**Cite this repository** if what you used was the data or the code. Use the Zenodo
**version** DOI, not the concept DOI, so the citation resolves to the deposit you
actually ran:

> Addison-Turner, D. C. (2026). *An optically independent administrative reference
> for validating built-surface products, and the tree-canopy bias it reveals*
> (version 1.0.0) [Data set and code]. Zenodo. https://doi.org/10.5281/zenodo.23072749

**What GitHub's "Cite this repository" button actually shows.** The repository
entry above, in APA and BibTeX, with the version and the GitHub URL, and with the
Zenodo DOI once it is added. It does **not** show the paper, and that is a
deliberate choice rather than an oversight.

GitHub renders `preferred-citation` *instead of* the top-level entry when one
exists. A `preferred-citation` naming the paper would therefore make the button
display an unpublished manuscript carrying no DOI and no URL, giving a visitor
nothing they can resolve, and it would hide the Zenodo DOI, which lives on the
top-level entry and is the one identifier the repository does have. So the paper's
entry is kept in `CITATION.cff` as a commented block, ready to uncomment, and the
button shows the thing a visitor has in front of them.

**On acceptance this flips, and the harness makes you do it.** Once the manuscript
stops carrying its DOI placeholder, `make_tables.py` fails until `CITATION.cff`
names the published paper under `preferred-citation` with its journal and article
DOI. It also fails, in the other direction, if a `preferred-citation` appears while
the paper is still unpublished. Neither state can drift quietly.

**Every shipped script carries the citation in its own header.** The author's name
and ORCID, the paper's title and intended venue, the repository URL and the licence
sit in the first dozen lines of each `.js`, `.py`, `.R` and `.sh` file. This is for
the Earth Engine scripts above all: they are pasted into a Code Editor, saved into
an account and shared from there as a link to a script, and nothing on that path
carries this README along. A reader who receives one otherwise has no way to tell
whose work it is, which paper it belongs to, or that it is MIT rather than
all-rights-reserved, which is what a file with no licence statement defaults to.
`make_tables.py` checks each header against the metadata rather than against a copy
of the expected words, so the name comes from the manuscript byline, the ORCID from
the same place the release-metadata check reads, and the URL from `CITATION.cff`. A
header that drifts from the citation it mirrors fails.

**The Zenodo DOI is absent rather than guessed**, in that file and in the
manuscript, because a wrong DOI is worse than a missing one and this project has
already been bitten by a concept-versus-version mix-up. `GITHUB_AND_ZENODO.md`
lists the four places it goes.

## Revisions in the final pass

Three corrections were made after the assertion harness and the county service were
re-queried. All three are recorded here because each changed printed values.

1. **The bound is truncated at 100 percent of cell area.** A cell cannot be more
   than wholly impervious, but 163 parcels in 33 cells carried a raw bound above
   100, to a maximum of 146.3, because a structure larger than one 30 m cell is
   charged in full to the cell holding its centroid. Those cells average 0.05 canopy
   cover, so they sit in the open: truncating them *steepens* the canopy gradient
   rather than flattening it. Truncation is applied in `make_tables.py::truncate()`
   to the bound, the garage-excluded bound, and every product-versus-bound breach
   indicator, so no reported quantity rests on an impossible bound. Values that moved:
   mean bound 25.3 to 25.1, mean shortfall 3.3 to 3.1, garage-excluded bound 19.3 to
   19.2, detection-failure coefficient +0.3113 to +0.3119, garage-excluded coefficient
   +0.3230 to +0.3236, conditioning specification −21.19 to −21.15, canopy on the
   bound −7.89 to −7.58, WorldCover breach 76.3% to 75.9%. The headline canopy
   coefficient on NLCD, −21.8958, does not involve the bound and did not move.

2. **"Residential parcels" is now justified from the roll, not from the use code.**
   The county's `UseCode` carries no coded-value domain and `ImprovementsDescription`
   is null throughout, so the codes cannot be read directly. Instead the frame is
   characterised by `TotalUnits`, `Bedrooms` and `Baths`: 24,021 of 24,088 parcels
   record at least one dwelling unit, **none records zero**, and 99.8 percent carry a
   bedroom or bathroom count. The 13.2 percent outside the dominant code are
   condominium-style units (median lot 0.02 acres, one unit, 2.2 bedrooms), not
   non-residential land. `parcel_extras.csv` holds these fields; it matches the
   analysis pull row for row on recorded garage area, which is asserted.

3. **Figure 4's subtitle claimed the product falls "three times faster" than the
   bound.** The true ratio is 2.05x on the endpoint fall and 2.22x on the decile
   slope, so the text now reads "more than twice as fast".

A frame-restriction ladder was added to Table 4. Restricting to single-parcel cells,
to the dominant use code, to lots of at least 0.05 acres, or to cells where truncation
does not bind moves the continuous coefficient only between −19.65 and −21.90, and
**raises** the detection-failure coefficient in every case, from +0.312 to between
+0.327 and +0.350. `make_tables.py` asserts that strengthening, so a future change
that silently weakened it would fail the harness.

## Two late additions and one caveat about coordinate precision

### The reference is now validated against an independent footprint product

`ms_footprint_validation.csv` holds 700 cells, 70 per canopy decile, with Microsoft
Building Footprints area summed within each 30 m cell alongside the recorded roof the
bound is built from. The asset is
`projects/sat-io/open-datasets/MSBuildings/US/California` (Awesome GEE Community
Catalog), 81,849 buildings inside the county bounding box.

Read on the 569 cells holding a single parcel, where the recorded roof and the detected
footprint describe the same structure, and on the MEDIAN ratio: a ratio of means is
dragged by multi-parcel cells and by a left tail.

| | median ratio | product exceeds the record | no building found |
|---|---|---|---|
| two lowest canopy deciles | **1.01** | 50.5% | 2.7% |
| two highest canopy deciles | **0.54** | 24.8% | 30.6% |

Where occlusion is not operating, an independent measurement of what stands on the ground
matches the assessor record and is as often above it as below, so the record is not
inflated. Under closed canopy the same product finds half as much and nothing at all in
three cells in ten. Mann-Whitney on the two bands gives p = 5.5e-08. Capture dates are
2018-2019 in both bands, so imagery epoch is not confounded with canopy. Since the
recorded roof is canopy-blind, the decline belongs to the imagery, not the record.

### Coordinate precision in the released row-level file

**`lon` and `lat` in `nevada_canopy_bias_rowlevel.csv` are rounded to four decimal
places**, a median position error of 3.9 m. That is fine for every analysis in the paper,
because the cell assignment `px` was computed upstream at full precision and is released
with the data. It is NOT fine for recomputing cell geometry: at a median
centroid-to-edge distance of 4.4 m, rounding at that scale misclassifies roughly one
parcel in five.

`parcel_edge_exact.csv` therefore carries the distance from each parcel centroid to the
nearest 30 m cell edge, computed from full-precision assessor centroids, along with the
cell indices. Those indices reproduce the released `px` for 99.99 percent of parcels,
which is the check that the two pipelines agree. **Any recomputation of cell geometry
should use that file, not the rounded coordinates.** `make_tables.py::straddle()` does.

This was found late: an earlier version of the straddle analysis recomputed edge
distances from the rounded coordinates and agreed with the corrected classification for
only 82 percent of parcels. The distributional figures barely moved (35.1 against 35.2
percent provably inside) because distance to a grid edge is uniform regardless of
coordinate noise, but the per-parcel subset changed and with it the regression on it.
