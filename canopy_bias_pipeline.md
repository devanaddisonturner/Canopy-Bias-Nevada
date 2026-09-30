# Canopy bias in built-surface products: pipeline and design

*Devan Cantrell Addison-Turner, ORCID [0000-0002-2511-3680](https://orcid.org/0000-0002-2511-3680), Department of Civil and Environmental Engineering, Stanford University. From the reproduction package for "An optically independent administrative reference for validating built-surface products, and the tree-canopy bias it reveals", prepared for GIScience & Remote Sensing. Repository: https://github.com/devanaddisonturner/Canopy-Bias-Nevada Code MIT, released data CC0 1.0.*

> **Status note, added 2026-09-28.** Working record, kept for provenance; the
> manuscript and `make_tables.py` are authoritative. The below-floor coefficient
> appears here as **+0.3113** and in the manuscript as **+0.3119**, the
> difference being the 100 percent ceiling of Equation 2 applied to the derived
> breach indicators after this document was written. The retractions recorded
> below stand.

Revision 4, 2026-09-27. The Nevada County assessor service turns out to publish far more than the design assumed, and three obstacles the earlier revisions treated as structural have dissolved.

## What changed, in order of importance

1. **There is no sampling step any more.** The qualifying population is 24,088 parcels and the service pages 2,000 at a time, so the whole census comes down in 13 requests. The largest error in this project was a spatially clustered sample; you cannot have sampling bias if you do not sample. The proportional-allocation grid, the staggered offsets and the population-validation step are all retired.
2. **The gravel-driveway objection is measured, and it is small.** The assessor publishes `RoadSurface`. In the frame, 22,607 of 24,088 parcels are "Pavement, Good" (93.9 percent) and only 468 are dirt or gravel (1.9 percent). Restrict to paved access and the referee's main alternative explanation is eliminated by construction rather than argued away.
3. **The floor test is roughly twice as strong as estimated, because storeys are real.** `Stories` is populated and the frame mean is 1.549, not the 2 an earlier revision assumed. With the garage added, the recorded structures imply 15 to 21 percent impervious in the containing pixel, against an earlier guess of 9.3 percent.
4. **Proposition 13 is settled and I was wrong about it.** Only 70 of 24,088 parcels have an improvement value below $20,000, which is 0.29 percent. The old filter was very nearly non-binding. Revision 2 called this a change you must make; that was overstated, and revision 3's downgrade was the right call.
5. **The national branch of the design fork is closed, for a reason that strengthens the paper.** See the literature section below.

## Why the existing NLCD validation cannot detect this error

From Wickham et al., *Thematic accuracy assessment of the NLCD 2019 land cover for the conterminous United States*, GIScience and Remote Sensing 60(1), 2181143, read in full via the open EPA author manuscript on PubMed Central.

The reference standard is **Google Earth photointerpretation**. The paper names it 51 times. The protocol is: one experienced interpreter labelled all 3,245 sample pixels, blind to the map label, with the pixel as the spatial support unit, explicitly using neighbourhood image context to assign the label.

The words **"tree canopy", "occlusion", "obscured", "hidden", "shadow", "tree cover", "lidar", "parcel", "assessor" and "building footprint" appear zero times in the paper.**

That is the whole argument. If a house is invisible under canopy in Google Earth imagery, it is invisible to the interpreter too. The interpreter labels the pixel forest, the map labels it forest, and the assessment records **agreement**. The error class this paper is about is invisible to the validation protocol by construction, because the reference medium shares the optical blind spot of the map being validated.

This closes the three-way fork decisively:

| Branch | Status |
|---|---|
| Already done in the literature | **No.** Canopy is not mentioned once, and there is no stratification of developed omission by vegetation context |
| Use the EPA national reference sample | **Closed.** It is photointerpretation, so it cannot serve as canopy-independent truth. Also n = 3,245 nationally across 22 strata, which is far too thin for a canopy-stratified analysis of developed omission |
| County design with an administrative reference | **Stands**, and now has a sharp motivation |

The contribution is therefore not "NLCD has error." It is: **NLCD's validation protocol is structurally incapable of measuring this error class, and here is a reference that can.** That is a much better paper.

Supporting numbers worth quoting: Level II overall accuracy 77.5 percent ± 1, Level I 83.1 percent ± 0.9, against primary reference label only. NLCD developed classes are defined by impervious cover, with class 21 open space being under 20 percent impervious.

The EPA reference data itself is real and public, at `pasteur.epa.gov/uploads/10.23719/1530414/NLCD2019_AA_RefData.zip` under the ScienceHub license, catalogued on data.gov, contact James Wickham. Worth having for context, but not usable as a reference standard here.

## The physical floor test

The assessor records a building. A building has a roof. A roof is impervious whether or not a satellite can see it. So measured impervious surface has a lower bound set by an administrative record that no tree can affect.

```
roof_m2      = (SquareFeetOnRecord / Stories + VehicleBuildingSquareFeet) * 0.092903
imp_floor_px = 100 * (sum of roof_m2 over all parcels in the 30 m pixel) / 900
```

A product reporting less than `imp_floor_px` is not observing less paving. It is failing to detect buildings that are recorded to exist.

**The support must match, and this is what an earlier revision got wrong.** Dividing the roof by the 20 m disc compares against an NLCD value that describes a 900 m2 pixel containing the neighbours. Different denominators. That version flags isolated houses and rarely flags dense ones whatever the canopy, and isolation correlates with canopy, so it replaces one confound with another. The pixel-summed version shares a denominator with the measurement and is the only one to report. `imp_floor_disc_pct` survives in the export as a diagnostic and must not appear in the paper.

**This is the second reason the census matters.** A sample misses the neighbours whose roofs share the pixel, so the pixel-level floor is only computable from the full population.

Conservatism, all pushing against finding an effect: porch and deck area is excluded, since a wooden deck may not be impervious; driveways, walkways and patios are excluded entirely; and `Stories` is taken at face value, which for a partial second storey overstates storeys and so understates the roof.

### What the floor implies, before any imagery is touched

| Storeys | n | Mean living sqft | Mean garage sqft | Implied footprint | Percent of a 900 m2 pixel |
|---|---|---|---|---|---|
| 1 | 11,905 | 1,583 | 408 | 1,991 sqft | **20.6** |
| 2 | 11,291 | 2,061 | 442 | 1,473 sqft | **15.2** |
| 3 | 846 | 2,757 | 516 | 1,435 sqft | 14.8 |
| 4 | 46 | 3,721 | 452 | 1,383 sqft | 14.3 |

Set that beside the county-wide NLCD structure measured in Earth Engine: the **median developed pixel in Nevada County is 8 percent impervious**, and **53 percent of developed pixels are below 10 percent**.

Treat that juxtaposition carefully. The county-wide developed figure includes class 21 open space, parks and large-lot rural land, so it is not the same population as the frame. The honest statement is that the recorded structures on these parcels imply 15 to 21 percent, and what NLCD actually reports **at these specific parcels** is exactly what the extraction step is for. Do not report the comparison as a result until the extraction is run.

### The blunt version, and what it means precisely

`zero_nlcd`: the product reports exactly zero impervious surface at a parcel with a recorded house. County diagnostics pin down the statement:

- Every developed pixel in the county has impervious above zero, and within developed pixels the value floors at 1, never 0.
- But impervious above zero does not require the developed class: 2.70 percent of county pixels have impervious above zero while not classed developed, which is 29 percent of all impervious-positive pixels.

So `zero_nlcd = 1` is strictly stronger than "not classified developed" and is a real statement about the impervious product, not a restatement of land cover.

## Data source

`https://maps.nevadacountyca.gov/arcgis/rest/services/web_public/Open_Data_Layers_Nevada_County_1/FeatureServer/200`, titled "Parcel Information", owner CountyofNevada, 64,401 polygon features, `maxRecordCount` 2,000, supports statistics and pagination, returns centroids in EPSG:3857.

**Fields that carry data:** `SquareFeetOnRecord` (47,414), `Stories` (46,348), `VehicleBuildingSquareFeet` (36,859), `PorchSquareFeet` (22,527), `RoadSurface` (53,427), `TotalImproveValue` (51,030), `YearBuilt` (44,546), `GISACRES` (64,374), `Acreage` (61,973), `TotalUnits` (55,518), plus `UseCode`, `HasSewer`, `WaterSource`, `Topography`, `PoolSpa`, `Bedrooms`, `Baths`.

**Fields present in the schema but entirely empty. Do not build on them:** `Floor1SquareFeet`, `Floor2SquareFeet`, `BasementSquareFeet`, `ImprovementsSquareFeet`. Each returns zero records with a value above zero. `Floor1SquareFeet` would have been the ideal footprint field and it is empty, which is why the floor goes through `SquareFeetOnRecord / Stories` instead.

### The frame

`SquareFeetOnRecord >= 400 AND Stories > 0 AND Stories <= 4 AND GISACRES > 0 AND GISACRES <= 0.5`

Filters on floor area and parcel size only. **Neither filter uses canopy, NLCD, or any remote-sensing input**, so selection cannot be correlated with the measurement error under study, and neither is tenure-related. That is the property the design needs. It is *not* the same as statistical independence from canopy, and an earlier version of this line claimed the stronger property without testing it: parcel acres correlates with canopy at **+0.283**, and mean canopy rises from 0.311 in the smallest acreage quartile to 0.503 in the largest. The consequence is a bound on scope rather than on validity, recorded in the limitations. `Stories <= 4` drops ten records with obvious data errors, one of which claims 32 storeys.

| | n |
|---|---|
| Qualifying frame | **24,088** |
| Built on or before 2019, the headline sample | **21,931** |
| Built after 2019, the placebo group | **589** |
| No year built recorded, excluded from both | **1,568** |
| Paved access | 22,607 |
| Dirt or gravel access | 468 |
| Improvement value below $20,000 | 70 |

The three groups sum to 24,088. An earlier draft of this document gave the
headline sample as 22,005 and the placebo as 2,083, which wrongly folded the
1,568 parcels with no recorded year into the post-2019 group. Including those
1,568 in the main sample moves the canopy coefficient from −18.49 to −18.75, so
the exclusion is immaterial, but the arithmetic must be stated correctly.

Frame means: 0.2738 acres, 1,856 sqft living area, 1.549 storeys, 428 sqft garage, $436,661 improvement value.

The **2,083 post-2019 parcels are a real negative control.** NLCD 2019 cannot see a house built in 2021 for a reason that has nothing to do with trees, so the detection-failure rate in that group should be high at *every* canopy level. If it instead tracks canopy the same way the main sample does, something is wrong with the whole design.

## What runs where

| Stage | Where | Why not Earth Engine |
|---|---|---|
| 1. Pull the population, compute roof, pixel floor, neighbour density | Browser console or any HTTP client | Earth Engine makes no outbound HTTP calls |
| 2. Raster extraction and export | **Earth Engine** | This is what it is for |
| 3. Regression and inference | R, or Python | `ee.Reducer.linearRegression` returns coefficients and residuals and **no standard errors of any kind** |

Note that the cloud sandbox used to develop this cannot reach ArcGIS services at all: the egress proxy returns 403 on CONNECT to `services.arcgis.com`, `pmc.ncbi.nlm.nih.gov`, `pasteur.epa.gov` and `mrlc.gov`. All of stage 1 therefore has to run from a normal browser.

### Stage 1

Run `run_full_analysis_browser.js`, which is the version in this package and does stages 1 and 2 in one pass: open the Earth Engine code editor, sign in, open the developer console, paste, press Enter. It pages the whole population from the county service, converts centroids from Web Mercator to WGS84, computes `roof_m2`, assigns each parcel to its EPSG:5070 30 m NLCD pixel, sums roof area per pixel, computes neighbour counts at 100 m and 250 m, then samples the rasters and writes `nevada_canopy_bias_rowlevel.csv` directly. It takes about twelve minutes.

The analysis was first run as the three separate stages below, and the stage headings are kept because they document where each quantity comes from. The stage 1 script of that route downloaded an intermediate CSV and is superseded by the single script above; it is deliberately not shipped, so follow the single-script route.

The EPSG:5070 Albers conversion in that file was verified numerically: the projection origin at 96 W, 23 N maps to (0, 0); Nevada City maps to (-2,114,076, 2,084,142), which is plausible for CONUS Albers; a 10 m offset returns 10 m and lands in the adjacent 30 m cell; a 94 m offset lands three cells away.

### Stage 2

In the staged route, upload the CSV as an Earth Engine table asset, set the path in `canopy_bias_extraction.js`, run, then press RUN on each of the three export tasks. Use the batch export, not `print`: interactive computation times out near five minutes. Keep the 1 m canopy map layer off while exporting, since rendering it competes with the reduction for the same compute budget.

### Stage 3

```r
library(fixest); library(data.table)
d <- fread("canopy_bias_nevada_r20.csv")

# QA. Do NOT filter on the absolute pixel count: a 20 m disc rasterises to 11,
# 12 or 13 cells at scale 10 depending on where it falls on the grid, so
# `n_nlcd == max(n_nlcd)` silently discards good parcels. An earlier draft of
# this document had that bug. Masking shows as DISAGREEMENT BETWEEN BANDS
# WITHIN A ROW, not as a low count.
d <- d[n_nlcd == n_dw & n_dw == n_wc & n_wc == n_canopy]

d_main    <- d[yr != "" & yr <= 2019]
d_placebo <- d[yr >  2019]
d_paved   <- d_main[grepl("^Pavement", road_surface)]

# Headline regression uses canopy_h2. NOTE: the claim that "the 2 m definition
# fits best" is NOT supported on the census. R2 for nlcd is 0.3203 with h2 and
# 0.3149 with h5; for below_floor it is 0.1009 with h2 and 0.1044 with h5, so h5
# fits BETTER on that outcome. The differences are about 0.005 either way and the
# coefficient barely moves (-21.90 vs -22.67). Threshold choice is close to
# irrelevant here, which is reassuring. Report it as a sensitivity, not a claim.
# and an earlier draft's code used h5 while its prose recommended h2.
m <- feols(nlcd_impervious ~ canopy_h2 + ac + sqft + slope + n_within_100m,
           data = d_main)
summary(m, vcov = "hetero")                                            # HC1
summary(m, vcov = vcov_conley(lat="lat", lon="lon", cutoff = 1))       # 1 km
summary(m, vcov = vcov_conley(lat="lat", lon="lon", cutoff = 2))       # 2 km
summary(m, vcov = vcov_conley(lat="lat", lon="lon", cutoff = 5))       # 5 km

# Primary result: detection failure against the support-matched floor.
f <- feols(below_floor_nlcd ~ canopy_h2 + ac + sqft + slope + n_within_100m,
           data = d_main)
summary(f, vcov = vcov_conley(lat="lat", lon="lon", cutoff = 1))

# Kills the gravel-driveway objection outright.
summary(update(f, data = d_paved), vcov = vcov_conley(lat="lat", lon="lon", cutoff = 1))

# Negative control. Run it on the CONTINUOUS outcome, not the binary one:
# below_floor sits near its ceiling in the post-2019 group (raw rates 0.71, 0.85,
# 0.87 by canopy tercile), so a null there is partly mechanical. The continuous
# outcome has no ceiling and gives -2.45 (t = -1.37) against -21.90 in d_main.
summary(feols(nlcd_impervious ~ canopy_h2 + ac + sqft + slope + n_within_100m,
              data = d_placebo),
        vcov = vcov_conley(lat="lat", lon="lon", cutoff = 1))

# The figure, within density stratum so isolation cannot do the work.
d_main[, dens := cut(n_within_100m, quantile(n_within_100m, 0:4/4), include.lowest = TRUE)]
d_main[, dec  := cut(canopy_h2,     quantile(canopy_h2,     0:10/10), include.lowest = TRUE)]
d_main[, .(zero = mean(zero_nlcd), below = mean(below_floor_nlcd), n = .N), by = .(dens, dec)]
```

`vcov_conley`'s `cutoff` is in kilometres.

Inference requirements: HC1 as a baseline; Conley spatial HAC at 1, 2 and 5 km, because neighbouring parcels share NLCD pixels and ignoring it understates the standard error by a factor of two and a half to three; a nonparametric bootstrap as a cross-check; and **no clustering on county** in a multi-county model, since three clusters is far below the thirty to fifty where cluster-robust inference is valid. Report per-county coefficients or use a wild cluster bootstrap. For the binary floor outcome, a linear probability model with Conley errors is the cleanest presentation, with logit as a robustness check only.

Report the canopy effect over the **interquartile range of observed canopy**, not the 0 to 1 coefficient, which extrapolates to a parcel that is 100 percent canopy and also has a house. Keep the coefficient in the table, not in the abstract.

## Earth Engine diagnostics already run

| Check | Result |
|---|---|
| Is Meta canopy masked off-canopy, which would break every mean? | **No.** `unmask(0)` moves a paved disc from 0.04498 to 0.04498 |
| Does `ee.Terrain.slope` handle 3DEP's geographic projection? | **Yes.** Steep canyon gives p5 3.2, p50 20.2, p95 38.2, p99 42.7 degrees |
| Is `USGS/3DEP/10m` an Image? | Yes, band `elevation`, nominal scale 10.31 m |
| GHSL units | m2 per 100 m cell, 0 to 10000, so divide by 100 |
| Any product masked over land? | No. Counts in a 20 m disc: NLCD 13, WorldCover 16, GHSL 13, Dynamic World 17 |
| `reduceResolution` on a Dynamic World median composite | **Fails.** A median composite carries no default projection. Set the source projection first |
| `reduceResolution` 30 m to 100 m maxPixels | Needs at least 1,069, so use 4,096. The default 1,024 fails silently |

### County-wide NLCD structure, Nevada County

| Quantity | Value |
|---|---|
| County pixels with impervious above 0 | 9.26 percent |
| County pixels classed developed (21 to 24) | 6.56 percent |
| Impervious above 0 but not developed | 2.70 percent of county, so 29 percent of impervious-positive pixels |
| Developed but impervious equal to 0 | 0 percent |
| Impervious percentiles within developed pixels | p25 = 2.0, p50 = 8, floors at 1 never 0 |
| Developed pixels below 10 percent impervious | 53 percent |
| Correlation of canopy with impervious within developed pixels | **−0.358** |

That last line is a free county-wide result needing no parcel data: the canopy relationship survives inside the developed mask, so it is not an artefact of the developed versus undeveloped classification boundary.

## Two corrections to the multi-product claim

**GHSL does not measure impervious surface.** It measures building surface. A fully paved downtown block returns NLCD 88.9 percent impervious against GHSL 37.1 percent built; a Truckee parcel returns NLCD 90.8 against GHSL 19.9. That is a difference in target quantity, not a bias, and putting GHSL on the same axis as NLCD impervious was a category error. The floor test is the right comparison for GHSL, because a roof is precisely what GHSL claims to measure, which makes `below_floor_ghsl` the fairest test in the set.

**Support matching was needed before the decision-rule claim was allowed.** An earlier revision compared a 30 m product against a 100 m product inside a 20 m disc and attributed the difference to the decision rule, which entangles resolution with rule. Every product is now aggregated to the common GHSL grid. On four synthetic test sites the matched values barely moved, but **four points settle nothing** and this project has already lost two findings that dissolved as n grew. The mechanism is implemented; whether the pattern survives is open.

## Known dead ends, do not retry

- **VIDA_COMBINED/USA footprints.** A 20 m disc returned 31 overlapping polygons totalling 36,000 m2 against a disc area of 1,257. Intersection area cannot exceed containing area, so the asset carries duplicated or non-building geometry.
- **`Floor1SquareFeet` and friends.** In the schema, entirely empty.
- **A near-zero-canopy control county.** Sacramento has only 4 of 174 developed locations above 50 percent canopy. Use Placer, which spans valley to Tahoe inside one assessor.
- **Canopy removal as a treatment.** Clearing is frequently part of development, so impervious genuinely increases and the design would score a true positive as an artefact. NLCD epochs are also not independent measurements.
- **Relaxing the parcel-size filter.** Pooling gives −13.29 by averaging in strata with 0.6 percent mean impervious. A floor effect diluting the estimate.
- **A sharp canopy threshold.** An earlier claim of a break near 50 percent was contradicted by Frisch-Waugh residualized deciles. But "the relationship is essentially linear", which this document previously stated, is **also wrong** and is retracted. See the curvature section in `canopy_bias_results.md`.
- **A stormwater impervious-area dataset for Nevada County.** All 221 layers in the county's ArcGIS Online organisation were listed; none carries impervious area. Nevada County is not an urbanised MS4 with a parcel-level stormwater fee, so this is expected. Placer County is still worth one check.

## Status of the headline number

**This has been recomputed. The result below supersedes the 26.15 figure that
appeared in earlier drafts of this document.**

The old 26.15 came from a spatially clustered sample of 4,010 with `canopy_h5`,
an improvement-value filter and an assumed two storeys. All four are superseded.

Current, on the 21,931-parcel census (built on or before 2019) with `canopy_h2`,
real storeys and a neighbour-density covariate:

| Quantity | Value |
|---|---|
| Canopy on NLCD impervious | **−21.90** (HC1 0.43; block 1 km 1.35, t = −16.2; block 2 km 1.99, t = −11.0) |
| Net of the nighttime-lights masking step | −18.13 (t = −13.5) |
| Canopy on below-floor | **+0.3113** (block 2 km 0.036, t = 8.7) |
| Post-2019 negative control, continuous outcome | −2.45 (t = −1.37) |
| OEHHA gap, zero canopy to full | +0.84 to −25.87 |

Report the canopy effect as a range of **18 to 22 points**, because controlling
for nighttime radiance may be over-control: canopy suppresses upward light
emission as well as reflected daylight, so that layer may be a mediator rather
than a confounder. See `canopy_bias_results.md` section 7.

## Remaining

1. ~~Run stage 1 and the extraction~~ **Done.** 24,088-parcel census extracted and analysed; see `canopy_bias_results.md`.
2. **Full Placer pull**, 124,261 parcels. A 3,600-parcel check replicates the effect, but the pooled estimate is distorted by valley-versus-mountain composition, so real neighbour density from the census is required before any Placer figure is quoted.
3. **Placer carries NO storeys field.** Verified. The floor test therefore does not transfer: forcing Nevada to an assumed storey count biases the coefficient upward by 24 percent, toward the hypothesis. Placer contributes the regression and OEHHA comparison only.
4. **One check on Placer County public works** for a parcel-level impervious-area record.
5. ~~The specification ladder and the west/east split rest on the superseded 4,010-parcel sample.~~ **Done.** Both re-run on the census. The ladder is in `canopy_bias_results.md` section 9e and `analyze_canopy_bias.py` section 12a; the earlier "three necessary, four unnecessary covariates" taxonomy did not survive and has been replaced by the actual table plus a disclosed asymmetry (the headline includes the covariate with the smallest shift and excludes one with a larger shift). The split is now −20.91 west and −19.84 east, tighter than the −26.2/−22.0 previously carried.
6. **Add `canopy_h10`** to the extract to complete the threshold sensitivity at the tall end. One band.
7. **Independent reproduction** before submission. Twenty-one substantive errors have been found and corrected during development, most of them mine, and the headline has never survived a round of scrutiny unchanged. The numbers have held; the prose around them is where the failures cluster, specifically sentences asserted once and then reused as grounds for not testing something.
