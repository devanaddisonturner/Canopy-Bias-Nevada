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
// Infrastructure vs. Natural Capital -- Signal Check v3
// Supersedes v1 (placer_county_signal_check.js) and v2 (signal_check_v2_corrected.js).
// Run at https://code.earthengine.google.com: paste, then click Run.
//
// What v3 adds over v2:
//  A. Probability-weighted driver attribution alongside the hard argmax class.
//     The driver layer publishes probability_1..7 per 1 km cell. Taking only the
//     argmax class systematically undercounts a minority driver such as
//     settlements and infrastructure, which is rarely dominant in a Sierra cell
//     but frequently present. In Placer County the soft estimate is 2,159 ha
//     against 1,186 ha hard, so the honest range is 2.1 to 3.8 percent, not a
//     single point estimate.
//  B. The canopy cost of development is decomposed into two independent terms:
//       SITING             = share of new development that was forested in 2000
//       CLEARING INTENSITY = share of that forest actually lost
//     v2 reported only their product, which conflates "development went where
//     the trees were" with "development removed the trees it found". These move
//     independently and have different policy implications.
//  C. Numerator and denominator of clearing intensity now share one canopy base
//     (treecover2000 >= 30 percent). In v2 the numerator counted Hansen loss on
//     any canopy while the denominator counted only >=30 percent canopy, which
//     produced clearing intensities above 100 percent in 12 California counties.
//  D. Cropland flag. Hansen counts orchards as tree cover, so in Central Valley
//     counties "tree cover loss" is largely orchard turnover rather than natural
//     capital loss. Any county with a high cropland share must be excluded from
//     a natural-capital framing or handled explicitly.
// ============================================================================

var COUNTIES = ['Placer', 'El Dorado', 'Nevada'];

var px = ee.Image.pixelArea().divide(10000);
var gfc = ee.Image('UMD/hansen/global_forest_change_2025_v1_13');
var loss = gfc.select('loss');
var loss19 = loss.and(gfc.select('lossyear').lte(19)); // aligned to the NLCD 2019 endpoint
var tc30 = gfc.select('treecover2000').gte(30);

var drivers = ee.Image('projects/landandcarbon/assets/wri_gdm_drivers_forest_loss_1km/v1_3_2001_2025');
var infra = drivers.select('classification').eq(6);
var pbands = ['probability_1','probability_2','probability_3','probability_4',
              'probability_5','probability_6','probability_7'];
var p6frac = drivers.select('probability_6')
  .divide(drivers.select(pbands).reduce(ee.Reducer.sum())); // sums to ~247, so normalise

var rel19 = ee.ImageCollection('USGS/NLCD_RELEASES/2019_REL/NLCD');
var lc01 = ee.Image(rel19.filter(ee.Filter.eq('system:index','2001')).first()).select('landcover');
var lc19 = ee.Image(rel19.filter(ee.Filter.eq('system:index','2019')).first()).select('landcover');
function dv(i){ return i.gte(21).and(i.lte(24)); }
var newDev = dv(lc19).and(dv(lc01).not());
var crop01 = lc01.gte(81).and(lc01.lte(82));

COUNTIES.forEach(function (name) {
  var geom = ee.FeatureCollection('TIGER/2018/Counties')
    .filter(ee.Filter.and(ee.Filter.eq('NAME', name), ee.Filter.eq('STATEFP','06'))).geometry();

  function ha(img){
    return ee.Number(img.multiply(px).reduceRegion({
      reducer: ee.Reducer.sum(), geometry: geom, scale: 30, maxPixels: 1e11}).values().get(0));
  }

  var total     = ha(loss);
  var infraHard = ha(loss.and(infra));
  var infraSoft = ha(loss.multiply(p6frac));
  var nd        = ha(newDev);
  var fInDev    = ha(newDev.and(tc30));
  var lossF     = ha(loss19.and(newDev).and(tc30));

  print('===== ' + name + ' County =====');
  print('Total canopy loss 2001-2025 (ha):', total);
  print('Infrastructure-driven loss, hard argmax (ha):', infraHard);
  print('Infrastructure-driven loss, probability-weighted (ha):', infraSoft);
  print('Infrastructure share, hard / soft (%):',
    ee.List([infraHard.divide(total).multiply(100), infraSoft.divide(total).multiply(100)]));
  print('Loss by dominant driver (ha):',
    loss.multiply(px).addBands(drivers.select('classification')).reduceRegion({
      reducer: ee.Reducer.sum().group({groupField: 1, groupName: 'class'}),
      geometry: geom, scale: 30, maxPixels: 1e11}));
  print('New development 2001-2019 (ha):', nd);
  print('SITING -- share of new development that was forested in 2000 (%):',
    fInDev.divide(nd).multiply(100));
  print('CLEARING INTENSITY -- share of that forest lost by 2019 (%):',
    lossF.divide(fInDev).multiply(100));
  print('Combined canopy cost (ha lost per 100 ha developed):',
    lossF.divide(nd).multiply(100));
  print('Cropland share of new development (%) -- orchard-turnover confound flag:',
    ha(newDev.and(crop01)).divide(nd).multiply(100));
});

// ---- Annual series: infrastructure-driven loss is steady, wildfire is episodic ----
var placer = ee.FeatureCollection('TIGER/2018/Counties')
  .filter(ee.Filter.and(ee.Filter.eq('NAME','Placer'), ee.Filter.eq('STATEFP','06')));
print('Placer, ALL canopy loss by year (ha):',
  loss.multiply(px).addBands(gfc.select('lossyear')).reduceRegion({
    reducer: ee.Reducer.sum().group({groupField: 1, groupName: 'year'}),
    geometry: placer.geometry(), scale: 30, maxPixels: 1e11}));
print('Placer, INFRASTRUCTURE-driven loss by year (ha):',
  loss.and(infra).multiply(px).addBands(gfc.select('lossyear')).reduceRegion({
    reducer: ee.Reducer.sum().group({groupField: 1, groupName: 'year'}),
    geometry: placer.geometry(), scale: 30, maxPixels: 1e11}));

Map.centerObject(placer, 9);
Map.addLayer(placer, {color: 'black'}, 'Placer County boundary', true, 0.6);
Map.addLayer(loss.and(infra).selfMask().clip(placer), {palette: ['ff0000']},
  'Infrastructure-driven canopy loss', true);
Map.addLayer(loss.and(drivers.select('classification').eq(5)).selfMask().clip(placer),
  {palette: ['ff9900']}, 'Wildfire-driven canopy loss', false);
Map.addLayer(newDev.selfMask().clip(placer), {palette: ['0000ff']},
  'NLCD new development 2001-2019', true);

// ============================================================================
// STATEWIDE SCAN -- uncomment to reproduce the 41-county table.
// Runs about four minutes at 30 m. Reduce to scale 120 for a faster screen.
// ============================================================================
// var stack = ee.Image.cat([
//   loss.multiply(px).rename('totalLoss'),
//   loss.and(infra).multiply(px).rename('infraLoss'),
//   tc30.multiply(px).rename('forest2000'),
//   newDev.multiply(px).rename('newDev'),
//   newDev.and(tc30).multiply(px).rename('forestInNewDev'),
//   loss19.and(newDev).and(tc30).multiply(px).rename('lossInNewDev'),
//   newDev.and(crop01).multiply(px).rename('cropIntoDev')
// ]);
// var ca = ee.FeatureCollection('TIGER/2018/Counties').filter(ee.Filter.eq('STATEFP','06'));
// Export.table.toDrive({
//   collection: stack.reduceRegions({collection: ca, reducer: ee.Reducer.sum(),
//                                    scale: 30, tileScale: 4}),
//   description: 'ca_county_infrastructure_canopy_scan',
//   selectors: ['NAME','totalLoss','infraLoss','forest2000','newDev',
//               'forestInNewDev','lossInNewDev','cropIntoDev']
// });
