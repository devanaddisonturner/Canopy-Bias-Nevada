# Results: canopy-driven under-detection of built surface, Nevada County

*Devan Cantrell Addison-Turner, ORCID [0000-0002-2511-3680](https://orcid.org/0000-0002-2511-3680), Department of Civil and Environmental Engineering, Stanford University. From the reproduction package for "An optically independent administrative reference for validating built-surface products, and the tree-canopy bias it reveals", prepared for GIScience & Remote Sensing. Repository: https://github.com/devanaddisonturner/Canopy-Bias-Nevada Code MIT, released data CC0 1.0.*

> **Status note, added 2026-09-28.** This is the working results record from the
> 2026-09-27 run, kept for provenance. The manuscript and `make_tables.py` are
> authoritative for every published value. **One number below has since changed:**
> the below-floor coefficient reads **+0.3113** here and **+0.3119** in the
> manuscript. The difference is the 100 percent ceiling of Equation 2, applied to
> the derived breach indicators after this document was written. The eleven
> headline values the manuscript prints were checked against this document term
> by term, and only that one differs. The retractions recorded below, in sections
> 9c and 9d, stand.

Run 2026-09-27 on the full parcel census. Every number below was computed in this session.

## You have results

The canopy effect survives density stratification, which the novelty check identified as the make-or-break test. It is large, present in every density stratum though not monotonically so in the densest, robust to how the floor is defined, and unchanged when restricted to paved access.

**On the negative control, read section 2 rather than this sentence.** An earlier
draft said the effect "vanishes" there. The defensible statement is narrower: on
the continuous outcome the post-2019 group gives −2.45 (t = −1.37) against −21.90
in the main sample, an 87 percent reduction that is not distinguishable from
zero. The binary below-floor outcome sits near its ceiling in that group and is
mechanically pushed toward a null, so it should not be quoted as the placebo.

**Revision 2, 2026-09-27.** A rival explanation was found in the NLCD production
metadata and tested. It accounts for about a sixth of the effect and leaves the
rest. Headline numbers are now reported as bounds. See section 7.

## Data

| | |
|---|---|
| Source | Nevada County assessor, `Open_Data_Layers_Nevada_County_1/FeatureServer/200` |
| Frame | `SquareFeetOnRecord >= 400 AND Stories > 0 AND Stories <= 4 AND GISACRES > 0 AND GISACRES <= 0.5` |
| Parcels | **24,088, the complete census**, pulled in 13 pages. No sampling |
| Spatial extent | Longitude −121.274 to −120.021, sd 0.4366. The biased sample that once inflated this result had sd 0.015 |
| Main sample | 21,931 built on or before 2019 |
| Negative control | 589 built after 2019 |
| Distinct NLCD pixels | 19,574, mean 1.539 buildings per pixel |
| Earth Engine sampling | 24,088 points, 25 chunks, zero failures |

Canopy, slope, Dynamic World and WorldCover were aggregated from native resolution to the 30 m sampling grid with `reduceResolution`; NLCD and GHSL were taken at native support.

## The physical floor

```
roof_m2      = (SquareFeetOnRecord / Stories + VehicleBuildingSquareFeet) * 0.092903
imp_floor_px = 100 * (sum of roof_m2 over all parcels in the 30 m pixel) / 900
```

Distribution across the census: p10 11.6, p25 15.8, **median 21.3**, p75 30.9, p90 42.1, mean 25.7 percent.

So the median parcel sits in an NLCD pixel whose recorded structures occupy 21.3 percent of it. Measured NLCD impervious over the same parcels averages 22.45 percent, and **58.8 percent of parcels fall below their own physical floor.**

## Headline 1: measured impervious against canopy

`nlcd_impervious ~ canopy + acres + floor_area + slope + neighbours_100m`, n = 21,931.

| Coefficient on canopy | −21.90 percentage points |
|---|---|
| HC1 standard error | 0.43, t = −51.4 |
| Spatial block 1 km | 1.354, t = **−16.2** |
| Spatial block 2 km | 1.993, t = **−11.0** |

**Do not quote the block figures.** They depend on where the arbitrary grid
origin falls. Across 25 origin offsets at a 2 km block size the headline SE
ranges from **1.637 to 2.191**, a 30 percent spread, moving t between −10.0 and
−13.4. The 1.993 above is one draw from that range and 1.679 is another. Conley
requires no origin choice and converges (2.2613 at 5 km against 2.2629 at 8 km,
a change under 0.1 percent), so **Conley is what the manuscript reports** and
block clustering is mentioned in the methods only, with the spread disclosed.
| R squared | 0.320 |

Spatial dependence inflates the standard error by a factor of three to five, as expected. The effect survives it comfortably.

Note this is **−21.90, not the −26.15** carried in earlier drafts. The old number was computed on a spatially clustered sample without a density control. It was inflated by about 4 points.

**Do not quote −21.90 on its own.** Net of the nighttime-lights masking step it
is −18.13 (t = −13.5), and whether that layer is a confounder or a mediator is
unresolved, so the effect should be reported as a range of **18 to 22 points**.
Section 7 has the argument and the full table.

## Headline 2: detection failure against a physical bound

`below_floor ~ canopy + acres + floor_area + slope + neighbours_100m`, linear probability model.

| | Coefficient | SE (2 km blocks) | t |
|---|---|---|---|
| Main sample, n = 21,931 | **+0.3113** | 0.0360 | 8.7 |
| Paved access only, n = 21,037 | +0.3085 | n/a | 26.4 (HC1) |
| Conservative floor, garage excluded | +0.3230 | 0.0370 | 8.7 |
| Canopy at 5 m threshold | +0.3532 | n/a | 13.2 (1 km) |
| **Post-2019 negative control, n = 589** | **−0.0001** | n/a | **0.00** |

Going from bare to full canopy raises the probability that NLCD reports less impervious surface than the recorded buildings physically occupy by **31 percentage points**, 95 percent interval roughly 24 to 38.

**The negative control, stated correctly.** An earlier draft of this document
called the placebo coefficient of −0.0001 "as clean as a placebo gets." That was
overstated and is corrected here.

The placebo group is well powered on the treatment: its canopy standard
deviation is 0.345, **higher** than the main sample's 0.291, with 39 percent
above half canopy. So the concern that post-2019 parcels might be uniformly bare
is dismissed by measurement.

But the below-floor outcome in the placebo group is **near its ceiling**. Raw
rates by canopy tercile are 0.706, 0.847, 0.872, against 0.465, 0.573, 0.726 in
the main sample. Every post-2019 building is invisible to a 2019 product, so the
baseline is already high and there is little room left for an effect to show. A
binary outcome pinned near one is mechanically pushed toward a null coefficient.

There is also a raw gradient in the placebo, and it is expected rather than
damning: canopy predicts the **pre-existing** impervious surface in the pixel,
independent of the focal building, so a post-2019 house in the woods sits in a
pixel that was already wooded in 2019. The controls absorb that channel and the
residual is zero, which is why the conditional coefficient is +0.036 (t = 0.52).

**Lead with the continuous outcome instead**, which has no ceiling and where the
comparison is like for like, both specifications carrying the same controls:

| | Main sample | Post-2019 placebo |
|---|---|---|
| NLCD impervious on canopy | **−18.49** (t = −13.1) | **−2.45** (t = −1.37) |

An **87 percent reduction**, and the placebo estimate is not distinguishable
from zero. That is the defensible version of this test.

## Headline 3: the assumption-free version

`zero_nlcd`, the product reporting exactly zero impervious surface at a parcel with a recorded house. Needs no roof arithmetic at all.

Coefficient on canopy **+0.1598**, 1 km t = 7.5, 2 km t = 5.8. The raw rate runs from **12.5 percent in the lowest canopy decile to 36.2 percent in the highest.**

## The decisive test: canopy within density stratum

The novelty check established that Uhl and Leyk already published built-up underestimation in low-density rural areas, and that canopy is collinear with rural. If canopy had no effect within density stratum, this work would have been a re-derivation of theirs.

Below-floor rate, by canopy quintile, within neighbour-density quartile:

| Density quartile | mean neighbours | Q1 lowest canopy | Q2 | Q3 | Q4 | Q5 highest canopy |
|---|---|---|---|---|---|---|
| 1 | 6.7 | 54.9 | 62.7 | 69.1 | 74.8 | **84.5** |
| 2 | 12.5 | 52.2 | 55.4 | 59.8 | 63.0 | **80.6** |
| 3 | 16.8 | 43.7 | 47.9 | 55.2 | 62.6 | **74.8** |
| 4 | 31.0 | 35.7 | 33.1 | 40.2 | 51.8 | **60.5** |

Measured NLCD impervious over the same cells:

| Density quartile | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|---|---|---|---|---|
| 1 | 27.7 | 18.6 | 14.3 | 11.8 | 7.3 |
| 2 | 29.5 | 23.8 | 19.7 | 16.1 | 9.5 |
| 3 | 33.9 | 25.6 | 20.5 | 16.7 | 11.1 |
| 4 | 46.4 | 38.2 | 31.1 | 23.5 | 15.7 |

**Canopy separates from density in every stratum.** The below-floor rate rises
with canopy in all four, by 30, 28, 31 and 25 points, and measured impervious
falls with canopy in all four. Density has its own effect, exactly as the prior
literature says, and canopy has a separable effect on top of it.

**It is NOT monotonic in the densest stratum.** That row dips from 35.7 to 33.1
between the first and second canopy quintiles before climbing to 60.5. Every
cell holds at least 574 parcels, so this is not sampling noise. It is consistent
with the convex functional form: the canopy effect in dense settlement has a
delayed onset.

On the density coefficient, be careful which standard error is quoted. Under
2 km block clustering it is indistinguishable from zero (t = −0.5) while canopy
carries t = 8.7, but **under HC1 density is significant at t = −2.7**. The
robust statement is the magnitude, not the significance: density moves the
below-floor outcome about **1 point** across its interquartile range (10 to 19
neighbours), against **31 points** for canopy across its range.

*Corrected 2026-09-27.* This section previously claimed "Monotonic in every
stratum," which was contradicted by the table printed immediately above it: the
old bottom row read 34.2, 32.3, 32.9, 42.7, 54.0, which is not monotone. Both
tables were also computed on all 24,088 rows with canopy quintiles cut *within*
each density stratum, while the rest of this document uses the 21,931-parcel
analysis sample. Sample and binning are now consistent with everything else
here, and stated. The load-bearing claim, that canopy separates from density,
survives unchanged. Only the word "monotonic" was wrong.

## Headline 4: severity tracks the decision rule

Mean reported value by canopy quintile, and the share of parcels below their physical floor:

| Product | Rule | Q1 value | Q5 value | Fall | Below-floor Q1 to Q5 |
|---|---|---|---|---|---|
| ESA WorldCover | hard class | 54.4 | **0.9** | −98% | 37 to **99** |
| NLCD impervious | continuous | 36.4 | 10.1 | −72% | 45 to 78 |
| Dynamic World | probability | 61.4 | 31.2 | −49% | 14 to 37 |
| GHSL built surface | building area | 20.6 | 12.2 | −41% | 69 to 78 |

The hard-classified product collapses to essentially zero under canopy. The probabilistic product degrades gently. That is the decision-rule pattern, now measured on 21,931 parcels rather than asserted from four synthetic points.

GHSL deserves separate comment: it measures **building** surface, which is exactly what the floor measures, making it the fairest comparison in the set. It fails the floor for 69 to 78 percent of parcels across the whole canopy range, which is a statement about GHSL's absolute calibration rather than about canopy.

## Full canopy decile table, main sample

All figures below are the analysis sample, n = 21,931, built on or before 2019.

| Decile | canopy | NLCD % | floor % | below % | zero % |
|---|---|---|---|---|---|
| 1 | 0.01 | 39.4 | 35.4 | 43.8 | 12.5 |
| 2 | 0.09 | 33.4 | 30.7 | 46.1 | 9.0 |
| 3 | 0.19 | 28.2 | 26.8 | 47.9 | 10.7 |
| 4 | 0.29 | 25.2 | 25.4 | 51.6 | 11.6 |
| 5 | 0.39 | 22.4 | 24.5 | 54.0 | 11.1 |
| 6 | 0.48 | 19.1 | 23.9 | 60.3 | 13.7 |
| 7 | 0.58 | 17.2 | 23.1 | 63.2 | 15.3 |
| 8 | 0.68 | 15.1 | 22.0 | 65.8 | 17.2 |
| 9 | 0.79 | 12.2 | 21.0 | 73.7 | 24.2 |
| 10 | 0.94 | 7.9 | 20.0 | 81.6 | 36.3 |

The floor falls from **35.4 to 20.0** between the lowest and highest canopy deciles, a fall of 43 percent, while measured NLCD impervious falls from **39.4 to 7.9**, a fall of 80 percent. The two series cross at decile 4 and diverge from there. That divergence is what the paper is about.

*Corrected 2026-09-27.* The floor column was previously empty, and the sentence beneath this table quoted 35.8 to 21.0 and 40.7 to 8.0, which are the figures for all 24,088 rows including the post-2019 and year-missing parcels, while the table itself is the 21,931-parcel analysis sample. Two samples in adjacent lines, with NLCD's lowest decile appearing as both 39.4 and 40.7. Everything here is now the analysis sample.

## 7. The rival explanation, found in the NLCD metadata and tested

The official MRLC metadata for NLCD 2019 percent impervious states that
nighttime lights imagery, DMSP for 2011 and VIIRS for 2016, was imposed on
existing NLCD data **"to exclude low density impervious areas outside urban and
suburban centers."**

That is a documented, intentional production step that deletes impervious
surface in exactly the rural exurban setting this study measures. It is a rival
explanation for everything above, and it is more specific than any confound
considered during the design.

It is also correlated with canopy, as expected: corr(canopy, VIIRS 2016) =
**−0.298**, corr(canopy, DMSP 2011) = −0.263. Mean VIIRS radiance falls
monotonically from 5.47 in the lowest canopy decile to 1.19 in the highest.

Controlling for both nighttime-lights layers, spatial block SEs at 2 km:

| Outcome | Base | + nighttime lights | + lights + elevation |
|---|---|---|---|
| NLCD impervious | −21.90 (t = −11.0) | **−18.49** (t = −13.1) | **−18.13** (t = −13.5) |
| Below floor | +0.3113 (t = 8.7) | **+0.2580** (t = 9.7) | **+0.2693** (t = 9.4) |
| Reports exactly zero | +0.1598 (t = 5.8) | +0.1531 (t = 5.2) | |
| Paved access only | | +0.2569 (t = 9.3) | |
| Post-2019 placebo | −0.0001 (t = 0.00) | +0.0361 (t = 0.52) | |

**The mask accounts for roughly one sixth of the effect and leaves five sixths.**
The t-statistics improve rather than degrade, because the standard errors shrink
more than the coefficients do.

**Report these as bounds, not as a single number.** Controlling for nighttime
radiance is arguably over-control: dense canopy suppresses upward light emission
as well as reflected daylight, so radiance may be a **mediator** of the canopy
effect rather than a confounder. If it is a confounder the effect is −18.1; if
it is a mediator the effect is −21.9. The honest statement is **18 to 22
percentage points**, and the mechanism question is worth a paragraph rather than
a footnote.

There is also a framing opportunity here. "A documented production step erases
development in forested rural areas, and here is the magnitude at 24,088
parcels" is a sharper contribution than "trees confuse the sensor," and the two
are compatible.

## 8. Four checks that came out in the study's favour

**The floor construction is conservative.** The floor is mechanically driven by
how many recorded buildings share the pixel, and that count falls with canopy:
corr(canopy, n_bldg_px) = −0.211, corr(canopy, imp_floor_px) = −0.267. So
high-canopy parcels face a **lower** bar and fail it more often anyway.
Controlling for the floor's own drivers raises the canopy coefficient:

| Specification | canopy on below-floor |
|---|---|
| Base | +0.3113 (t = 27.3) |
| + buildings in pixel | +0.3544 (t = 32.4) |
| + the floor itself | **+0.4082** (t = 38.2) |

The headline is a conservative bound.

**Elevation is not a confound.** corr(canopy, elevation) = +0.097 only, and mean
elevation moves from 1,187 m in the lowest canopy decile to 1,316 m in the
highest. Adding it changes the coefficient from −18.49 to −18.13. A concern
raised during review and dismissed by measurement.

**Pixel assignment error is not driving the result.** Each parcel is sampled at
its centroid pixel. Larger parcels are more likely to have the building sit away
from that centroid, and parcel acres correlates with canopy at **+0.283**, so
differential assignment error is a live threat rather than a hypothetical one.
Earlier notes asserted that assignment error was canopy-independent. That was
wrong, and it was never tested; it is corrected here.

The clean test uses the scale-free outcome, because the below-floor rate does not
depend on how much impervious surface a pixel contains:

| Parcel size | n | canopy on below-floor | t |
|---|---|---|---|
| Acres Q1, smallest | 5,669 | +0.3371 | +14.0 |
| Acres Q2 | 5,942 | +0.3163 | +13.7 |
| Acres Q3 | 5,176 | +0.3458 | +14.9 |
| Acres Q4, largest | 5,144 | +0.3158 | +15.3 |

The coefficient is **flat**, spanning 0.030 on a base of 0.32, or 9 percent, with
no trend in parcel size. If assignment error were generating the result it would
have to be constant across a 2.4-fold range of parcel area, which it cannot be.

The continuous outcome does vary by parcel size, from −34.06 in Q1 to −13.93 in
Q4, and that variation should **not** be read as bias being worse on small
parcels. The physical floor's own canopy gradient varies across the same
quartiles, from −16.36 to −1.00, so smaller parcels simply have more impervious
surface in the pixel for the product to miss. The scale-free measure is the one
that answers the confound, and it is invariant.

**The canopy gradient is not a reflection of the real roof gradient.** Canopy
does predict a genuinely lower physical floor, at −7.89 (t = −23.5) with the
headline controls: high-canopy pixels really do hold less recorded roof.
Measured impervious could therefore be tracking something real. It is not.
Adding the floor itself to the headline regression leaves the canopy coefficient
at **−21.19** (t = −49.7) against −21.90 without it, a change of 0.71 points.
The floor's own coefficient in that regression is **+0.089**, meaning a pixel
with one point more recorded roof shows about a tenth of a point more measured
impervious. Attenuation from measurement error in the floor and the floor's
limited residual variance after controls both push that figure toward zero, so it
is a lower bound and must not be quoted as evidence that the product ignores
roofs outright. What it does establish is the point needed here: conditioning on
the real roof does not absorb the canopy gradient.

*Correction recorded.* An earlier working note computed the "excess gradient not
explained by real roof" as −21.90 minus −7.89 = −14.00. Subtracting coefficients
across two separate regressions is not a decomposition and that figure is
discarded. The regression control, −21.19, is the correct quantity and it is
stronger, not weaker.

**The consolidated script reproduces exactly.** `buildStack` from
`run_full_analysis_browser.js` was executed as written against 400 parcels and
six bands; maximum absolute difference from the stored dataset was **0**.

## 9. A mechanism test that is NOT available in this county

Deciduous canopy is transparent to leaf-off Landsat and evergreen is not, so a
deciduous versus evergreen contrast would discriminate occlusion from spectral
mixing. **It cannot be run here.** Nevada County is overwhelmingly conifer:

| NLCD forest class | n in the main sample |
|---|---|
| Deciduous (41) | **50** |
| Evergreen (42) | 3,075 |
| Mixed (43) | **67** |

Fifty deciduous parcels is not a test. This needs a mixed-forest county, which
is a reason to choose the replication site for forest composition rather than
just for adjacency. Within the evergreen subset the effect is +0.2024 (t = 8.0),
smaller than the full sample because those parcels are already the extreme cases.

## 9b. The error becomes steadily more negative with canopy. It does NOT change sign.

Two published findings currently sit awkwardly together. Nowak and Greenfield
(2010) report that NLCD **underestimates** impervious cover nationally. The
EnviroAtlas comparison across 18 metropolitan areas, and Culler, Wickham, Nash
and Clement (2024), report that NLCD **overpredicts** relative to high-resolution
reference data in urban settings.

Measured against the physical floor, the gap swings monotonically across the
canopy range and crosses zero:

| Canopy decile | canopy | NLCD | floor | NLCD − floor | % of parcels above floor |
|---|---|---|---|---|---|
| 1 | 0.01 | 39.4 | 35.4 | **+4.00** | 56 |
| 3 | 0.19 | 28.2 | 26.8 | +1.42 | 52 |
| 4 | 0.29 | 25.2 | 25.4 | −0.27 | 48 |
| 6 | 0.48 | 19.1 | 23.9 | −4.75 | 40 |
| 8 | 0.68 | 15.1 | 22.0 | −6.91 | 34 |
| 10 | 0.94 | 7.9 | 20.0 | **−12.15** | 18 |

Lowest two deciles: **+3.34** points. Highest two: **−10.46** points. A swing of
**13.8 points**, crossing zero near 30 percent canopy.

### RESOLVED, 2026-09-27, against a published full-impervious reference

The roof-only floor cannot settle the sign question, for reasons given below.
A published external reference can, and it does.

**The reference.** California OEHHA Impervious Surface Coefficients, derived from
330 residential sites in Sacramento, Irvine and Santa Cruz, digitised by analysts
from high-resolution aerial photography within 9-acre sampling boxes:

```
ISC = 0.2449 + 0.352 * log10(dwelling units per acre), valid 1 to 50 du/acre
```

It includes driveways, walkways and patios, which the roof floor does not. Its
9-acre box is close to the 7.76 acres enclosed by the 100 m neighbour radius
already in the dataset, so `du/acre = (n100 + 1) / 7.76`. It is a function of
density only and **takes no canopy or remote-sensing input**, which is the
property that lets it serve as a reference: it cannot inherit the occlusion error
being measured. That is deliberately weaker than statistical independence, which
does not hold, since canopy and neighbour density correlate at −0.211. 19,545 parcels, 89 percent of the main sample, fall in its valid
density range.

| Canopy decile | canopy | du/ac | OEHHA predicted | NLCD | NLCD − OEHHA | NLCD − roof floor |
|---|---|---|---|---|---|---|
| 1 | 0.01 | 3.03 | 39.24 | 40.09 | **+0.84** | +3.72 |
| 3 | 0.19 | 2.60 | 37.15 | 29.72 | −7.43 | +2.31 |
| 5 | 0.39 | 2.33 | 36.03 | 23.36 | −12.67 | −1.37 |
| 8 | 0.67 | 2.09 | 34.85 | 15.79 | −19.06 | −6.55 |
| 10 | 0.93 | 2.06 | 34.50 | 8.63 | **−25.87** | −11.72 |

**Three things follow, and the first is a calibration check worth reporting.**

At the lowest canopy decile NLCD sits **+0.84 points** from the published
reference, with **50.1 percent** of parcels above it and 49.9 below. A near
perfect median match. Where optical sensing should work, NLCD and an
independently derived reference agree almost exactly. That validates the
reference and the comparison at the same time.

At the highest canopy decile NLCD understates by **25.87 points**, and only
**3.2 percent** of parcels exceed the reference.

**So the bias does not change sign in this county.** It runs from approximately
zero at low canopy to about −26 at high canopy. The sign-flip hypothesis is not
supported here, and the swing of **26.7 points** is nearly double the 15.4 points
the roof-only floor suggested.

**The two references bracket the effect.** The roof alone is incontrovertible: at
the top decile the recorded roofs occupy 20.34 percent of the pixel and NLCD
reports 8.63, a shortfall of at least **11.7 points** that requires no assumption
about driveways. Adding published driveway and patio coefficients puts it at
about **26 points**. Report the bracket, not a single number.

Caveats. OEHHA predicts a neighbourhood average from density, not a parcel-level
value, so it has no within-density variation by construction. Its three source
cities are not Sierra foothills, and one of them, Santa Cruz, is itself forested,
so the coefficients may absorb a little of the same bias, which would make this
estimate conservative. And it was digitised from aerial photography, which shares
the optical medium even though manual interpretation handles canopy far better
than automated Landsat classification.

### Why the roof-only floor could not settle this

The floor is roof area only. It excludes driveways, walkways and patios, so it
is a lower bound on true impervious surface. "NLCD above the floor" means **no
under-detection is demonstrated**, not that NLCD overpredicts. At +4.00 points
above a roof-only bound, NLCD may still sit well below true impervious surface.
The +4.00 figure is seductive and will be misread.

Worse for the neat story: the roof-only shortfall is probably **not**
canopy-independent. Driveway length grows with setback, setback grows with lot
size, and lot size correlates with canopy at +0.283. If anything the floor understates true
impervious *more* on wooded lots, which deepens the negative end and does nothing
for the positive one.

What the table does license: **the bias becomes monotonically more negative as
canopy rises, by roughly 14 points across the range.** That is a real and useful
result. It is also, note, the same underlying finding as sections 1 and 2 in a
third framing, not independent evidence.

The sign change remains a **hypothesis**, formed by combining this gradient with
the published overprediction in dense urban settings (the EnviroAtlas metro
comparison; Culler et al. 2024). It is a good hypothesis and it would reconcile
Nowak and Greenfield (2010) against that literature. Testing it requires a
reference that captures **all** impervious surface, not just roofs, which means
either high-resolution imagery digitised in a validation subsample or a
stormwater utility's measured impervious area. Present it as a hypothesis the
data motivate, never as a result.

## 9c. The relationship is NOT linear, and an earlier claim that it was is retracted

Previous notes in this project said the canopy relationship is "essentially
linear," on the strength of Frisch-Waugh residualized deciles. That is a weak
test and it was run on the old, smaller sample. On the census the curvature is
statistically clear.

`nlcd_impervious ~ canopy + canopy² + acres + floor_area + slope + density`:

| Sample | canopy | canopy² | t on canopy² | marginal effect at canopy 0 → 1 |
|---|---|---|---|---|
| Full census, n = 21,931 | −30.37 | **+9.07** | +6.1 | −30.4 → −12.2 |
| Exact 0 and 1 dropped, n = 20,507 | −24.13 | +3.41 | +2.1 | −24.1 → −17.3 |
| Outer 5 percent dropped, n = 18,563 | −24.90 | +4.07 | +1.9 | −24.9 → −16.8 |
| With nighttime lights controlled | −23.41 | +5.25 | +3.7 | −23.4 → −12.9 |

F for the quadratic term on the full census is 38.4, and a cubic term adds more
still (t = −5.6, F = 31.7).

**Read this carefully in two directions.**

The curvature is partly carried by the mass at the endpoints: 5.1 percent of
parcels sit at exactly zero canopy and 1.2 percent at exactly one. Removing them
roughly halves the quadratic term and takes it to the edge of significance. So
the shape is real but not as pronounced as the full-census fit suggests.

And the practical consequence for the headline is small. Predicted values from
the linear and quadratic models differ by at most **1.97 points** anywhere in the
range, and they agree at both ends. **The linear coefficient of −21.90 remains a
fair summary of the total effect across the canopy range.** What is not fair is
describing the relationship as linear.

**The substantive reading is that the first increments of canopy do most of the
damage.** The marginal effect is roughly −25 to −30 points per unit canopy near
zero, falling to −12 to −17 near full cover. That is consistent with a detection
process that fails early: once canopy passes a modest level, the product has
already lost the surface, and further canopy has less left to hide.

**The below-floor outcome curves the other way, and much harder.** Regressing the
binary below-floor indicator on canopy and canopy² gives a linear term of
**+0.0219** and a quadratic of **+0.3097 (t = 8.3)**. Almost the entire
relationship is quadratic, so detection failure against the physical floor
*accelerates* with canopy rather than decelerating. Report both shapes; they are
different phenomena and the contrast is informative.

## 9d. Canopy threshold: the choice barely matters, and the stated justification was wrong

Earlier notes said "the 2 m definition fits best, which favours spectral mixing
over occlusion." On the census that is not supported.

| Canopy definition | measured impervious | R² | below-floor | R² |
|---|---|---|---|---|
| ≥ 2 m (used) | **−21.90** (t = −51.4) | 0.3203 | **+0.3113** (t = 27.3) | 0.1009 |
| ≥ 5 m | −22.67 (t = −53.8) | 0.3149 | +0.3532 (t = 29.8) | **0.1044** |
| continuous height, metres | −1.64 per m (t = −55.6) | 0.3146 | n/a | n/a |

The 2 m threshold fits marginally better on measured impervious; the 5 m
threshold fits marginally better on below-floor. Both differences are about
0.005 in R², and the coefficient moves by less than a point. **The finding is
robust to the threshold rather than dependent on it**, which is the reassuring
reading, but the specific justification previously given was an assertion that
the data do not support. Report the table as a sensitivity and drop the claim.

**A gap worth recording.** The census extract carries canopy at 2 m and 5 m plus
continuous height, but **not the 10 m threshold**, because
`run_full_analysis_browser.js` omits it while the older
`canopy_bias_extraction.js` includes it. The threshold sensitivity is therefore
incomplete at the tall end. Adding `canopy_h10` costs one band in the next run.

## 9e. The control set, justified on the census, with one asymmetry disclosed

The headline specification is `nlcd ~ canopy + acres + floor area + slope +
neighbour density`. Nothing in these notes previously justified that choice. An
earlier taxonomy of "necessary" and "unnecessary" covariates existed but was
computed on the superseded 4,010-parcel stratified sample and has been removed
rather than carried forward. Re-run on the census, adding one covariate at a
time:

| Specification | canopy | R² | shift |
|---|---|---|---|
| canopy alone | −31.44 | 0.1890 | n/a |
| + parcel acres | −24.60 | 0.2920 | +6.84 |
| + building floor area | −23.39 | 0.2995 | +1.21 |
| + terrain slope | −22.24 | 0.3095 | +1.16 |
| **+ neighbour density within 100 m (headline)** | **−21.90** | 0.3203 | +0.34 |
| + storeys | −20.59 | 0.3294 | +1.30 |
| + garage area | −20.94 | 0.3317 | −0.35 |
| + paved access | −20.93 | 0.3331 | +0.01 |
| + improvement value | −21.17 | 0.3396 | −0.24 |
| + elevation | −20.82 | 0.3414 | +0.36 |
| + neighbour density within 250 m | −21.27 | 0.3444 | −0.45 |

Parcel acres does nearly all the work, absorbing 6.84 of the 9.54-point
difference between the bivariate and the full specification. Everything after it
moves the coefficient by about a point or less.

**The asymmetry, stated rather than buried.** The headline includes neighbour
density, which shifts the coefficient by **+0.34**, the smallest shift in the
table, and excludes storeys, which shifts it by **+1.30**, more than either
slope or floor area. That ordering does not favour the paper's claim being
included as drawn, so it is disclosed here rather than defended. Two facts bear
on it. Neighbour density is in the specification because it is the variable the
decisive within-stratum test is built on, not because of its shift. Storeys is
the weakest-measured field in the assessor extract, defaulted to 2 where absent,
and the same field enters the roof footprint used to build the floor, so it is
the one covariate that is partly a construction input rather than an independent
control.

Neither argument requires the reader's agreement, because the choice does not
change the conclusion:

| Specification | canopy | HC1 t |
|---|---|---|
| Headline | −21.90 | −51.4 |
| Headline + storeys | −20.59 | n/a |
| Every covariate available | **−21.27** | −49.0 |
| Net of the nighttime-lights mask | −18.13 | −13.5 |

The reported range of **18 to 22 points** covers every specification above. No
choice of controls in the available data moves the estimate outside it, and the
low end of the range comes from the nighttime-lights adjustment rather than from
any covariate.

## 10. What the error costs a downstream user

An illustrative magnitude calculation, not a calibrated hydrologic study, using
the NRCS TR-55 composite curve number for connected impervious area and the NRCS
runoff equation. The mapping from impervious fraction to curve number is
published, not invented here.

The reference is `max(NLCD, floor)`, so no error is claimed where NLCD already
exceeds the roof-only bound. **Because the floor excludes driveways, walkways
and patios, every figure below is a lower bound on the true understatement.**

**Share of reference runoff that an NLCD-based estimate captures**, woods in good
condition, by soil group and storm depth:

| Storm (in) | HSG A | HSG B | HSG C | HSG D |
|---|---|---|---|---|
| 1 | 53% | 65% | 69% | 77% |
| 2 | 67% | 69% | 82% | 87% |
| 3 | 68% | 76% | 87% | 90% |
| 4 | 67% | 81% | 89% | 92% |
| 6 | 69% | 86% | 92% | 95% |

Two patterns worth the discussion section. The error is **largest on well-drained
soils**, because where the pervious fraction actually infiltrates, getting the
impervious fraction wrong dominates the answer; on heavy clay the ground runs off
anyway and the mistake matters less. And the error is **largest for small,
frequent storms**, which are the ones that govern water-quality permitting and
first-flush design rather than flood peaks.

**By canopy decile**, 3-inch storm, soil group B:

| Canopy decile | canopy | NLCD imp % | reference imp % | Q captured |
|---|---|---|---|---|
| 1 | 0.01 | 39.4 | 49.8 | 82% |
| 5 | 0.39 | 22.4 | 31.5 | 79% |
| 8 | 0.68 | 15.1 | 26.4 | 70% |
| 10 | 0.94 | 7.9 | 22.0 | **60%** |

In the most canopied decile an NLCD-based runoff estimate recovers three fifths
of the reference. Sensitivity to the pervious assumption is modest: substituting
open space in good condition for woods moves the whole-sample figure from 76 to
81 percent.

**Volume**, one 3-inch storm, soil group B: 85.6 acre-feet unaccounted across the
21,931 frame parcels, 12.5 of it in the top canopy decile alone. That is one
storm and only residential parcels under half an acre, not a county water budget.

The point is not the absolute volume, which is modest. It is that the error is
**systematic, one-directional, concentrated in the wildland-urban interface, and
invisible to the product's own validation**. Anyone using these layers for
stormwater permitting, first-flush design, TMDL allocation or WUI exposure
modelling inherits it silently.

## 11b. The two headline results are one finding in two framings

`below_floor` is by construction the indicator `1{nlcd_impervious <
imp_floor_px}`. It correlates with measured impervious at **−0.670**, and the
floor itself varies with canopy at −0.267. So the below-floor result is not a
statistically independent confirmation of the impervious result. It is the same
result re-expressed against a physical threshold.

That is still worth doing, because the re-expression is what converts a
continuous association into a falsifiable claim: the product reports less
impervious surface than the recorded buildings provably occupy. But it should be
presented as an **interpretation** of the primary result, not as a second
independent finding, and a referee will make this point if the paper does not.

The genuinely independent checks are the density stratification, the placebo,
the paved-access restriction, and the multi-product comparison.

## 11. The 1,568 parcels with no year built

The frame is 24,088; the main sample 21,931; the placebo 589. The remaining
**1,568 parcels, 6.5 percent, carry no year built** and fall out of both. The
arithmetic should be stated explicitly rather than left for a reader to notice.

They are a genuinely different group: lower canopy (0.359 against 0.442), higher
measured impervious (32.8 against 21.7), denser surroundings (19.2 neighbours
against 16.1) and smaller lots. They are the more urban tail.

Including them changes nothing that matters:

| Sample | n | NLCD on canopy | below-floor on canopy |
|---|---|---|---|
| Main, nulls excluded, as reported | 21,931 | −18.49 (t = −44.5) | +0.2580 (t = 22.4) |
| Nulls included | 23,499 | −18.63 (t = −46.1) | +0.2553 (t = 22.9) |
| Entire frame | 24,088 | −18.75 (t = −44.8) | +0.2470 (t = 22.9) |

Fourth-decimal movement. Report the exclusion, report this table, move on.

## 10b. Conley spatial HAC, and a claim of mine that was wrong

I said repeatedly that Conley errors were a convention gap rather than a
validity one, because block clustering is "generally the more conservative
choice." **That was asserted, never checked, and it is wrong.**

| Cutoff | Conley SE | Block SE | Larger |
|---|---|---|---|
| 1 km | **1.4382** | 1.3490 | Conley |
| 2 km | 1.8981 | **1.9851** | Block |
| 5 km | **2.2601** | 2.0298 | Conley |

Conley is larger at two of the three cutoffs. Neither dominates, so report both.

All three outcomes under Conley:

| Outcome | coefficient | 1 km | 2 km | 5 km |
|---|---|---|---|---|
| Measured impervious | −21.8958 | t = −15.2 | t = −11.5 | **t = −9.7** |
| Below floor | +0.3113 | t = +11.2 | t = +9.0 | **t = +7.7** |
| Reports exactly zero | +0.1598 | t = +7.5 | t = +5.8 | **t = +4.8** |

The result holds under the most demanding specification: Conley at a 5 km
cutoff still gives t = −9.7 on the headline.

It also took **four seconds** to compute on the full census. I listed it as an
outstanding item for the entire project.

## Limitations, stated plainly

1. **Pixel assignment is by parcel centroid.** A building is assumed to sit in the 30 m pixel containing its parcel centroid. Parcels average 0.27 acres, slightly larger than a pixel, so assignment error exists in both directions. It is **not** canopy-independent, because acres correlates with canopy at +0.283, so this was tested rather than assumed. The detection-failure coefficient is flat across acreage quartiles (+0.3371, +0.3163, +0.3458, +0.3158), which assignment error could not produce across a 2.4-fold range of parcel area (section 8). It adds noise. Parcel polygons, which the service does serve, would remove it.
2. ~~Standard errors are spatial block-cluster, not Conley.~~ **Resolved, then superseded.** Conley HAC is computed for all three outcomes; the headline holds at t = −9.7 at a 5 km cutoff. The claim that "block clustering is generally the more conservative of the two" was wrong. The later comparison of Conley *against* specific block values was also ill-posed: the block SE moves 30 percent with an arbitrary grid origin, so neither estimator "wins" at a given cutoff. Conley is principled here and converges; the manuscript reports Conley only.
3. **Canopy is measured on a 30 m cell centred on the parcel**, not on the exact NLCD Albers pixel. Up to a half-pixel offset.
4. **Canopy comes from an optical product** (Meta and WRI). Measurement error in the treatment attenuates toward zero, so this works against the finding rather than for it.
5. **Single county.** Placer is the replication site: 124,261 qualifying parcels,
   sd(longitude) 0.4361 against Nevada's 0.4366, and complementary canopy mass
   (Placer median 0.066 with a quarter at exactly zero, against Nevada's 0.437).
   A 3,600-parcel check reproduces the effect. Three verified constraints:
   Placer publishes **no storeys**, so the floor test does not transfer there;
   its `Acres` field is populated for only 22 percent of records while
   `GIS_Acres` covers 99.7 percent; and its pooled coefficient is distorted by
   valley-versus-mountain composition (−20.37 valley, −34.98 mountain, −41.00
   pooled), so density or region controls are mandatory before quoting any
   Placer figure.
6. **The negative control has n = 589.** Report it on the continuous outcome, −2.45 (t = −1.37) against −21.90. The below-floor version sits near its ceiling in that group, with raw rates of 0.71, 0.85 and 0.87 by canopy tercile, so its −0.0001 null is partly mechanical and should not be quoted. On the zero outcome it returns −0.219 with t = −2.2, a sign reversal rather than a null, which deserves a sentence rather than a footnote.
7. **The floor assumes recorded structures exist as recorded.** Demolitions not reflected in the assessment roll would produce spurious breaches. The assessment roll is the current one.

8. **The frame is sub-half-acre residential parcels, and the estimate should not be read as county-wide.** `GISACRES <= 0.5` is what makes the floor test meaningful, because on a large parcel the centroid pixel is mostly one owner's land and a recorded roof says little about the pixel. But acres correlates with canopy at +0.283, and inside the frame the continuous coefficient declines monotonically with parcel size, from −34.06 in the smallest quartile to −13.93 in the largest. Extrapolated past the 0.5-acre cut, the effect on larger residential parcels is likely smaller than the headline. The detection-failure coefficient is flat across the same quartiles at +0.32, so the *existence* of the effect generalises within the frame even though its magnitude does not. Claims in the paper should be scoped to dense small-lot residential settlement, which is also where these products are used for stormwater and equity work.

## What this changes

The paper exists. Draft the introduction around the density-stratified table, because that is the result the prior literature does not contain, and around the negative control, because that is what converts an association into a detection claim.

Two numbers in earlier drafts must be retired everywhere: the canopy coefficient is **−21.90**, not −26.15, and the analysis rests on a **census of 24,088**, not a sample of 4,010.
