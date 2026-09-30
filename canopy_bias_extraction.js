// ---------------------------------------------------------------------------
// Devan Cantrell Addison-Turner, ORCID 0000-0002-2511-3680
// Department of Civil and Environmental Engineering, Stanford University
//
// From the reproduction package for "An optically independent administrative
// reference for validating built-surface products, and the tree-canopy bias it
// reveals", a manuscript prepared for GIScience & Remote Sensing. Not yet
// published; cite the repository until it is. Citation metadata: CITATION.cff.
//
// https://github.com/devanaddisonturner/Canopy-Bias-Nevada
// Code MIT, released data CC0 1.0. This header travels with the file because an
// Earth Engine script does: it is pasted into a Code Editor and can be shared
// from there, where the README and LICENSE do not follow it.
// ---------------------------------------------------------------------------
// ============================================================================
// CANOPY BIAS IN BUILT-SURFACE PRODUCTS -- EARTH ENGINE EXTRACTION STEP
// Revision 2, 2026-09-26. Rewritten after a diagnostic audit.
//
// WHAT EARTH ENGINE CANNOT DO, so do not look for it here:
//   - fetch the assessor parcels (Earth Engine makes no outbound HTTP calls)
//   - draw the proportional spatial sample (needs population counts from the
//     county REST service)
//   - produce ANY standard error. ee.Reducer.linearRegression returns
//     coefficients and residuals only. HC1, cluster-robust and Conley spatial
//     HAC errors all happen outside. See canopy_bias_pipeline.md.
//
// THE SAMPLING PROBLEM IS RETIRED. ArcGIS returns records in internal order,
// which is spatially clustered, and a naive pull of the first N parcels once
// sampled a single town and inflated the canopy coefficient from -26 to -37.
// The fix is not better sampling, it is taking the census: the qualifying
// population is 24,088 parcels and the service pages 2,000 at a time, so the
// whole thing comes down in 13 requests.
//
// WHERE TO RUN, AND WHAT TO RUN INSTEAD
// -------------------------------------
// This is an EARTH ENGINE CODE EDITOR script: paste it into the script pane at
// code.earthengine.google.com, click Run, then press RUN on each queued task in
// the Tasks tab. It is not a browser-console script.
//
// It is also not the route to follow. This file is the Earth Engine step as it
// was actually run, kept for the record, and it needs an uploaded table asset
// built by a two-stage process whose first stage, stage1_pull_nevada_parcels.js,
// IS NOT IN THIS PACKAGE. Earlier revisions of this header said "Run
// stage1_pull_nevada_parcels.js", which sent a reader to a file that is not here.
//
// The shipped route is run_full_analysis_browser.js. It does the parcel pull and
// the Earth Engine sampling in one pass, in the browser developer console, and
// produces nevada_canopy_bias_rowlevel.csv from nothing in about 12 minutes. Use
// that. Read this one to see what the Earth Engine half does.
//
// WHAT CHANGED IN REVISION 2
//   1. Adds the PHYSICAL FLOOR TEST, against a SUPPORT-MATCHED floor computed
//      in stage 1: the summed recorded roof area of every parcel in the same
//      30 m NLCD pixel, over 900 m2. A product reporting less than that is
//      failing to detect buildings recorded to exist, and the gravel-driveway
//      objection cannot explain it. An earlier revision divided the roof by
//      the DISC instead, which flagged isolated houses and rarely flagged
//      dense ones whatever the canopy. That version survives only as
//      imp_floor_disc_pct and must not be reported.
//   2. Adds SUPPORT-MATCHED product comparison at 100 m. The revision 1 design
//      compared a 30 m product and a 100 m product inside a 20 m disc, which
//      cannot separate decision rule from pixel size. Now every product is
//      also aggregated to the common GHSL grid.
//   3. Exports year built and improvement value, which revision 1 loaded and
//      then silently dropped from the selector list.
//   4. Adds valid-pixel counts so partially masked regions can be dropped
//      rather than silently averaged over whatever pixels survived.
//   5. Runs three disc radii in one pass. The radius sensitivity test has been
//      outstanding since the beginning.
//
// DIAGNOSTICS RUN 2026-09-26, recorded so nobody repeats them:
//   - Meta canopy is NOT masked off-canopy. unmask(0) changes a paved disc
//     from 0.04498 to 0.04498. The unmask below is belt and braces for tile
//     edges, not a correction.
//   - ee.Terrain.slope on 3DEP handles the geographic projection correctly.
//     A steep canyon returns p5 3.2, p50 20.2, p95 38.2, p99 42.7 degrees.
//   - USGS/3DEP/10m is an Image, band 'elevation', nominal scale 10.31 m.
//   - GHSL built_surface is m2 per 100 m cell, 0 to 10000. Divide by 100.
//   - No product masks over land here. Counts in a 20 m disc: NLCD 13,
//     WorldCover 16, GHSL 13, Dynamic World 17.
//
// TEST HARNESS RESULT, four synthetic parcels, run 2026-09-26. This confirms
// the code computes what it claims. It is NOT evidence: the buildings were
// invented to exercise the logic, not read from the assessor.
//
//   site                canopy_h2  NLCD   DW     WC    GHSL  floor%  below?
//   downtown paved        0.00     88.9   74.0  100.0  37.1   6.01   no
//   wooded residential    1.00      0.0    2.9    0.0   0.0   6.76   ALL FOUR
//   mixed                 0.00     81.7   71.6   88.7  26.1   8.26   no
//   Truckee east          0.00     90.8   68.4   88.3  19.9   7.51   no
//
// FOUR POINTS SETTLE NOTHING. The pattern above is suggestive: hard-classified
// products appear to collapse (WorldCover 100 to 0) while the probabilistic one
// degrades gently (Dynamic World 74 to 2.9), and the support-matched 100 m
// values barely move (NLCD 88.9 to 82.8 open, 0 to 0.41 wooded). This project
// has already lost two findings that dissolved as n grew. Do not repeat that.
// The table proves the code runs; it proves nothing about the world.
//
// COUNTY-WIDE NLCD STRUCTURE, Nevada County, run 2026-09-26:
//   impervious > 0                                 9.26% of county pixels
//   classed developed (21-24)                      6.56%
//   impervious > 0 but NOT developed               2.70% (29% of impervious)
//   developed but impervious == 0                  0%
//   impervious within developed: p25 = 2.0, p50 = 8, floors at 1 never 0
//   developed pixels below 10% impervious          53%
//   corr(canopy, impervious) WITHIN developed      -0.358
// Impervious is not a mask of the developed class, so zero_nlcd is a real
// statement about the impervious product. And the canopy relationship survives
// inside the developed mask, so it is not an artefact of the developed versus
// undeveloped boundary. That last number is a free county-wide result that
// needs no parcel data at all.
// ============================================================================

// ---- 1. INPUT ---------------------------------------------------------------
// Upload nevada_parcels_population.csv as an Earth Engine table asset. It carries
// every field this script needs already computed: roof_m2, pixel_roof_m2,
// imp_floor_px, n_within_100m, storeys, road_surface, yr.
//
// NEITHER that CSV NOR the script that built it ships in this package, for the
// reason in the header: run_full_analysis_browser.js supersedes both by doing the
// parcel pull and the Earth Engine sampling in one pass. If you want this file's
// input anyway, the released nevada_canopy_bias_rowlevel.csv carries the same
// per-parcel fields for the 24,088-record frame, and the county parcel service is
// the authority for anything it does not.
//
// IT IS THE WHOLE POPULATION, NOT A SAMPLE. 24,088 qualifying parcels come down
// in 13 pages of 2,000, so there is nothing to sample and no sampling bias to
// guard against. The proportional-allocation machinery is retired.
var PARCELS = ee.FeatureCollection('users/REPLACE_ME/nevada_parcels_population');

var COUNTY  = 'Nevada';
var RADII   = [10, 20, 40];   // metres. 20 is the headline; 10 and 40 are the
                              // sensitivity test that has never been run.
//
// INTERPRETIVE WARNING on radius. The radius sweep tests how sensitive the
// REGRESSION is to the measurement footprint. It does not affect the floor
// test, which is now computed on the fixed 30 m NLCD pixel in stage 1 and is
// independent of the disc entirely.

// The stage-1 CSV carries parcel CENTROIDS, so this stays false. The source
// layer does serve polygons (esriGeometryPolygon, 64,401 features), and
// switching to them is a straightforward upgrade if the parcel-shaped
// measurement footprint is wanted: change stage 1 to returnGeometry=true and
// upload the shapefile instead. Containment of the building no longer depends
// on it, because the floor is computed on the pixel rather than the region.
var PARCELS_ARE_POLYGONS = false;

// STOREYS_DEFAULT is gone. The Nevada County assessor publishes a real Stories
// field, populated for 46,348 parcels, and the frame mean is 1.549, not the 2
// an earlier revision assumed. That assumption understated every roof by about
// 23 percent. roof_m2 now arrives from stage 1, computed as
// (SquareFeetOnRecord / Stories + VehicleBuildingSquareFeet) * 0.092903.
// Porch area is excluded to keep the bound conservative: a wooden deck is not
// necessarily impervious.

var county = ee.FeatureCollection('TIGER/2018/Counties')
  .filter(ee.Filter.and(ee.Filter.eq('NAME', COUNTY), ee.Filter.eq('STATEFP', '06')));
var geom = county.geometry();

// ---- 2. CANOPY --------------------------------------------------------------
// Three thresholds. NOTE: "the 2 m version fits best" was asserted early in
// this project and is NOT supported on the census. h2 fits marginally better on
// measured impervious, h5 marginally better on the below-floor outcome, both by
// about 0.005 in R2. The result is robust to the threshold rather than
// dependent on it. Original (unsupported) reasoning follows: favours spectral
// over occlusion: low vegetation suppresses detection too, and pure occlusion
// would require tall trees directly over the roof.
var ch = ee.ImageCollection('projects/meta-forest-monitoring-okw37/assets/CanopyHeight')
           .filterBounds(geom).mosaic().unmask(0);   // see diagnostic note above
var canopy = ch.gte(2).rename('canopy_h2')
  .addBands(ch.gte(5).rename('canopy_h5'))
  .addBands(ch.gte(10).rename('canopy_h10'))
  .addBands(ch.rename('canopy_height_m'));

// ---- 3. TERRAIN -------------------------------------------------------------
// Slope is a NECESSARY covariate: canopied parcels sit on steeper ground and
// steep ground reads as less impervious. Aspect is not necessary but is cheap.
var dem   = ee.Image('USGS/3DEP/10m');
var slope = ee.Terrain.slope(dem).rename('slope');
var north = ee.Terrain.aspect(dem).multiply(Math.PI / 180).cos().rename('northness');

// ---- 4. BUILT-SURFACE PRODUCTS, NATIVE SUPPORT ------------------------------
var n19 = ee.Image(ee.ImageCollection('USGS/NLCD_RELEASES/2019_REL/NLCD')
  .filter(ee.Filter.eq('system:index', '2019')).first());
var nlcdImp = n19.select('impervious').rename('nlcd_impervious');          // 30 m, continuous
var nlcdDev = n19.select('landcover').gte(21).and(n19.select('landcover').lte(24))
  .multiply(100).rename('nlcd_developed');                                 // 30 m, hard class

var dw = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
  .filterBounds(geom).filterDate('2019-01-01', '2020-12-31')
  .select('built').median().multiply(100).rename('dw_built');              // 10 m, probability

var wc = ee.Image(ee.ImageCollection('ESA/WorldCover/v200').first())
  .select('Map').eq(50).multiply(100).rename('wc_built');                  // 10 m, hard class

var ghslRaw = ee.Image(ee.ImageCollection('JRC/GHSL/P2023A/GHS_BUILT_S')
  .filter(ee.Filter.eq('system:index', '2020')).first()).select('built_surface');
var ghsl = ghslRaw.divide(100).rename('ghsl_built_pct');                   // 100 m, m2 -> pct

// IMPORTANT, and this corrects an earlier framing error. GHSL built_surface
// measures BUILDING surface, not impervious surface. A fully paved downtown
// block returns NLCD 88.9 percent impervious but GHSL 37.1 percent built, and
// a Truckee parcel returns NLCD 90.8 against GHSL 19.9. That gap is a
// difference in target quantity, not a bias. Do NOT place GHSL on the same
// axis as NLCD impervious. The physical floor test below is the correct and
// fair comparison for GHSL, because a roof is exactly what GHSL claims to
// measure.

// NOTE: VIDA_COMBINED/USA was tested and REJECTED. A 20 m disc returned 31
// overlapping polygons totalling 36,000 m2 against a disc area of 1,257 m2.
// Intersection area cannot exceed containing area, so the asset carries
// duplicated or non-building geometry. Do not use it without provenance work.

// ---- 5. BUILT-SURFACE PRODUCTS, SUPPORT-MATCHED AT 100 m --------------------
// Revision 1 compared NLCD at 30 m against GHSL at 100 m inside a 20 m disc
// and attributed the difference to the decision rule. That inference is not
// available at mismatched support: a 20 m disc cannot resolve anything inside
// a 100 m GHSL cell, so GHSL was being scored on a neighbourhood average while
// NLCD was scored on the parcel. Aggregating everything to the GHSL grid makes
// the decision-rule claim testable rather than assumed.
// maxPixels 4096, not the default 1024: a 30 m to 100 m aggregation needs 1069
// and silently fails below that. This exact bug cost a run earlier in the
// project.
// A median composite carries NO default projection, so reduceResolution fails
// on Dynamic World with "the input does not have a valid default projection".
// Caught by the test harness, 2026-09-26. Every input therefore gets its
// source projection set explicitly before aggregation.
var g100     = ghslRaw.projection();
var nlcdProj = n19.select('impervious').projection();
var dwProj   = ee.Image(ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
  .filterBounds(geom).filterDate('2019-01-01', '2020-12-31').first())
  .select('built').projection();
var wcProj   = ee.Image(ee.ImageCollection('ESA/WorldCover/v200').first())
  .select('Map').projection();

function to100(img, srcProj) {
  return img.setDefaultProjection(srcProj)
            .reduceResolution({reducer: ee.Reducer.mean(), maxPixels: 4096})
            .reproject({crs: g100});
}
var matched = to100(nlcdImp, nlcdProj).rename('m100_nlcd_impervious')
  .addBands(to100(nlcdDev, nlcdProj).rename('m100_nlcd_developed'))
  .addBands(to100(dw, dwProj).rename('m100_dw_built'))
  .addBands(to100(wc, wcProj).rename('m100_wc_built'))
  .addBands(ghsl.rename('m100_ghsl_built_pct'));

// ---- 6. STACK ---------------------------------------------------------------
var stack = canopy.addBands(slope).addBands(north)
  .addBands(nlcdImp).addBands(nlcdDev).addBands(dw).addBands(wc).addBands(ghsl)
  .addBands(matched);

// A second stack of counts. These detect MASKING only: the count is taken at
// the requested 10 m scale, so an unmasked region returns the same number for
// every band regardless of native resolution (13 in a 20 m disc). A count
// below that number means the product was masked there and the mean was taken
// over whatever pixels survived, which is a row to drop, not to trust.
var qaCount = nlcdImp.rename('n_nlcd')
  .addBands(dw.rename('n_dw'))
  .addBands(wc.rename('n_wc'))
  .addBands(ch.rename('n_canopy'));

// ---- 7. EXTRACT, ONE EXPORT PER RADIUS --------------------------------------
RADII.forEach(function (R) {

  var regions = PARCELS.map(function (f) {
    var g = PARCELS_ARE_POLYGONS ? f.geometry() : f.geometry().buffer(R);
    return ee.Feature(g, f.toDictionary()).set('region_m2', g.area(1));
  });

  var scored = stack.reduceRegions({
    collection: regions, reducer: ee.Reducer.mean(), scale: 10, tileScale: 16
  });

  var counted = qaCount.reduceRegions({
    collection: scored, reducer: ee.Reducer.count(), scale: 10, tileScale: 16
  });

  var out = counted.map(function (f) {

    // --- THE PHYSICAL FLOOR TEST -------------------------------------------
    // A recorded building has a roof. A roof is impervious. So the measured
    // impervious fraction has a floor that is set by the assessor record and
    // is independent of anything the satellite can see.
    // imp_floor_px arrives from stage 1 and is the SUPPORT-MATCHED floor: the
    // summed recorded roof area of every parcel falling in the same 30 m NLCD
    // pixel, over 900 m2. That is the comparison that is actually valid,
    // because it shares a denominator with what NLCD reports. The disc version
    // is kept as a diagnostic only and must not be reported.
    var floorPx   = ee.Number(f.get('imp_floor_px'));
    var region    = ee.Number(f.get('region_m2'));
    var floorDisc = ee.Number(f.get('roof_m2')).divide(region).multiply(100).min(100);

    var c = f.geometry().centroid(1).coordinates();
    return f.set({
      lon: c.get(0),
      lat: c.get(1),
      radius_m: R,
      imp_floor_disc_pct: floorDisc,
      // The headline indicators, against the support-matched floor. 1 means the
      // product reports less impervious surface than the recorded buildings in
      // that pixel physically occupy.
      below_floor_nlcd: ee.Number(f.get('nlcd_impervious')).lt(floorPx),
      below_floor_dw:   ee.Number(f.get('dw_built')).lt(floorPx),
      below_floor_wc:   ee.Number(f.get('wc_built')).lt(floorPx),
      below_floor_ghsl: ee.Number(f.get('ghsl_built_pct')).lt(floorPx),
      // The blunt version, which needs no roof arithmetic at all: a product
      // reporting exactly zero at a parcel with a recorded house.
      zero_nlcd: ee.Number(f.get('nlcd_impervious')).eq(0),
      zero_dw:   ee.Number(f.get('dw_built')).eq(0),
      zero_wc:   ee.Number(f.get('wc_built')).eq(0)
    }).setGeometry(null);
  });

  Export.table.toDrive({
    collection: out,
    description: 'canopy_bias_' + COUNTY.toLowerCase().replace(/\s/g, '_') + '_r' + R,
    fileFormat: 'CSV',
    selectors: [
      'apn', 'lon', 'lat', 'radius_m', 'region_m2',
      'ac', 'sqft', 'storeys', 'garage_sqft', 'yr', 'improve_val',
      'use_code', 'road_surface', 'units',
      'roof_m2', 'px', 'pixel_roof_m2', 'n_bldg_in_px', 'imp_floor_px',
      'n_within_100m', 'n_within_250m',
      'canopy_h2', 'canopy_h5', 'canopy_h10', 'canopy_height_m',
      'slope', 'northness',
      'nlcd_impervious', 'nlcd_developed', 'dw_built', 'wc_built', 'ghsl_built_pct',
      'm100_nlcd_impervious', 'm100_nlcd_developed', 'm100_dw_built',
      'm100_wc_built', 'm100_ghsl_built_pct',
      'imp_floor_disc_pct',
      'below_floor_nlcd', 'below_floor_dw', 'below_floor_wc', 'below_floor_ghsl',
      'zero_nlcd', 'zero_dw', 'zero_wc',
      'n_nlcd', 'n_dw', 'n_wc', 'n_canopy'
    ]
  });
});

print('Parcels in:', PARCELS.size());
print('Three export tasks queued, one per radius. Press RUN on each in Tasks.');
print('Interactive computation times out near five minutes. Do not print the');
print('reduction itself, and keep the canopy layer switched off while exporting.');

// ---- 8. INSPECTION LAYERS ---------------------------------------------------
// Keep these OFF while exporting. Rendering a 1 m canopy mosaic competes with
// the reduction for the same compute budget and caused repeated timeouts.
Map.centerObject(county, 10);
Map.addLayer(county, {color: 'black'}, 'County boundary', true, 0.6);
Map.addLayer(nlcdImp.clip(geom), {min: 0, max: 100, palette: ['ffffff', '3182bd']},
  'NLCD impervious %', false);
Map.addLayer(ch.gte(5).selfMask().clip(geom), {palette: ['2e7d32']},
  'Canopy >= 5 m', false);
Map.addLayer(PARCELS, {color: 'red'}, 'Sampled structures', true);
