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
// Measurement check: does NLCD's developed class miss exurban development?
// Independent reference: JRC Global Human Settlement Layer built-up surface.
//
// HOW TO RUN: paste into https://code.earthengine.google.com and click Run.
// Numeric output appears in the Console tab on the right.
//
// RETRACTED RESULT -- READ BEFORE USING THIS SCRIPT.
// This script once produced a headline of "30.9 percent of GHSL built-surface
// growth falls outside NLCD developed land, correlating with forest cover at
// r = 0.52." THAT NUMBER IS AN ARTEFACT and must not be cited. It comes from
// allocating built-surface growth proportionally to the NLCD developed
// fraction of each cell. Under a strict binary rule the same quantity is
// 2.6 percent, a twelvefold collapse. The script is retained only as a record
// of a dead end. The project's actual results are in canopy_bias_results.md.
// ============================================================================

// ---- Independent built-up reference (JRC GHSL, 100 m, produced separately from NLCD)
var ghsl   = ee.ImageCollection('JRC/GHSL/P2023A/GHS_BUILT_S');
var b2000  = ee.Image(ghsl.filter(ee.Filter.eq('system:index','2000')).first()).select('built_surface');
var b2020  = ee.Image(ghsl.filter(ee.Filter.eq('system:index','2020')).first()).select('built_surface');
var growth = b2020.subtract(b2000).max(0).divide(10000);   // hectares of built surface per cell

// ---- NLCD developed classes 21-24, single production run (2019 release).
// Note: the 2021 release contains only the 2021 image, so a 2001 filter against
// it returns null. The historical years live in the 2019 release.
var rel19 = ee.ImageCollection('USGS/NLCD_RELEASES/2019_REL/NLCD');
var lc01  = ee.Image(rel19.filter(ee.Filter.eq('system:index','2001')).first()).select('landcover');
var lc19  = ee.Image(rel19.filter(ee.Filter.eq('system:index','2019')).first()).select('landcover');
function dv(i){ return i.gte(21).and(i.lte(24)); }
var dev19 = dv(lc19);

// Fraction of each 100 m GHSL cell that NLCD calls developed, so built-surface
// growth is allocated proportionally rather than by nearest neighbour.
var devFrac = dev19.reduceResolution({reducer: ee.Reducer.mean(), maxPixels: 4096})
                   .reproject({crs: b2020.projection()});

var tc30 = ee.Image('UMD/hansen/global_forest_change_2025_v1_13')
             .select('treecover2000').gte(30);
var forestFrac = tc30.reduceResolution({reducer: ee.Reducer.mean(), maxPixels: 4096})
                     .reproject({crs: b2020.projection()});

var px = ee.Image.pixelArea().divide(10000);

function countyGeom(name){
  return ee.FeatureCollection('TIGER/2018/Counties')
    .filter(ee.Filter.and(ee.Filter.eq('NAME', name), ee.Filter.eq('STATEFP','06')))
    .geometry();
}

// ---- Per-county detail -------------------------------------------------------
['Placer', 'El Dorado', 'Nevada'].forEach(function(name){
  var geom = countyGeom(name);
  function s(img, sc){
    return ee.Number(img.reduceRegion({
      reducer: ee.Reducer.sum(), geometry: geom, scale: sc, maxPixels: 1e11
    }).values().get(0));
  }
  var total   = s(growth, 100);
  var outside = s(growth.multiply(ee.Image(1).subtract(devFrac)), 100);
  var outFor  = s(growth.multiply(ee.Image(1).subtract(devFrac)).multiply(forestFrac), 100);

  print('===== ' + name + ' County =====');
  print('GHSL built-surface growth 2000-2020 (ha):', total);
  print('NLCD new developed land 2001-2019 (ha):', s(dev19.and(dv(lc01).not()).multiply(px), 30));
  print('Share of built growth OUTSIDE NLCD developed land (%):',
        outside.divide(total).multiply(100));
  print('Share of built growth outside NLCD AND on forest (%):',
        outFor.divide(total).multiply(100));
});

// ---- Statewide table ---------------------------------------------------------
var stack = ee.Image.cat([
  growth.rename('ghslTotal'),
  growth.multiply(ee.Image(1).subtract(devFrac)).rename('ghslOutside'),
  growth.multiply(ee.Image(1).subtract(devFrac)).multiply(forestFrac).rename('ghslOutsideForest'),
  forestFrac.multiply(px).rename('forestHa'),
  px.rename('countyHa')
]);
var ca = ee.FeatureCollection('TIGER/2018/Counties').filter(ee.Filter.eq('STATEFP','06'));
var table = stack.reduceRegions({
  collection: ca, reducer: ee.Reducer.sum(), scale: 100, tileScale: 4
}).map(function(f){
  var tot = ee.Number(f.get('ghslTotal'));
  return ee.Feature(null, {
    county:            f.get('NAME'),
    forest_pct:        ee.Number(f.get('forestHa')).divide(f.get('countyHa')).multiply(100),
    ghsl_growth_ha:    tot,
    missed_pct:        ee.Number(f.get('ghslOutside')).divide(tot).multiply(100),
    missed_forest_pct: ee.Number(f.get('ghslOutsideForest')).divide(tot).multiply(100)
  });
}).filter(ee.Filter.gt('ghsl_growth_ha', 20)).sort('forest_pct');

print('Statewide: built-surface growth NLCD does not see, by county', table);

print(ui.Chart.feature.byFeature(table, 'forest_pct', ['missed_pct'])
  .setChartType('ScatterChart')
  .setOptions({
    title: 'Built-surface growth outside NLCD developed land vs county forest cover',
    hAxis: {title: 'County forest cover 2000 (%)'},
    vAxis: {title: 'Built growth NLCD does not classify as developed (%)'},
    pointSize: 5, legend: 'none', trendlines: {0: {showR2: true, visibleInLegend: true}}
  }));

// ---- Map ---------------------------------------------------------------------
var nevada = ee.FeatureCollection('TIGER/2018/Counties')
  .filter(ee.Filter.and(ee.Filter.eq('NAME','Nevada'), ee.Filter.eq('STATEFP','06')));
Map.centerObject(nevada, 10);
Map.addLayer(nevada, {color: 'black'}, 'Nevada County boundary', true, 0.6);
Map.addLayer(growth.multiply(ee.Image(1).subtract(devFrac)).selfMask().clip(nevada),
  {min: 0, max: 0.2, palette: ['ffffcc','fd8d3c','bd0026']},
  'Built growth NLCD misses', true);
Map.addLayer(dev19.selfMask().clip(nevada), {palette: ['3182bd']},
  'NLCD developed 2019', false);
