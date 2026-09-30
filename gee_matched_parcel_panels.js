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
// Figure 1 panels. Run in the browser console at code.earthengine.google.com
// (window.ee is available there). Produces six getThumbURL links, three per
// site: NAIP aerial, Meta/WRI canopy height, NLCD 2019 percent impervious.
//
// The two parcels are a MATCHED PAIR drawn from 3,530 candidate matches in the
// analysis sample and selected for TYPICALITY, not contrast: their NLCD values
// (38 and 1 percent) are exactly the medians of the low-canopy and high-canopy
// groups. The selection is implemented in make_tables.py (matched_pair_selection),
// which reproduces the 3,530 candidate matches, the group medians and this
// pair, and asserts them against the values printed in the manuscript.
//
//   low  APN 040-050-027  canopy 0.04  floor 20.5%  NLCD 38%  1,521 sqft 0.29ac 1998
//   high APN 045-300-033  canopy 1.00  floor 22.7%  NLCD  1%  1,470 sqft 0.29ac 1998
// ============================================================================
const ee = window.ee;
const SITES = {
  low:  { lon: -120.09190, lat: 39.35480 },
  high: { lon: -120.20670, lat: 39.34660 }
};

const naip = ee.ImageCollection('USDA/NAIP/DOQQ')
   .filterDate('2018-01-01', '2024-01-01').mosaic();          // bands R,G,B,N
const ch   = ee.ImageCollection('projects/meta-forest-monitoring-okw37/assets/CanopyHeight')
   .mosaic();                                                 // band cover_code, metres
const imp  = ee.Image('USGS/NLCD_RELEASES/2019_REL/NLCD/2019').select('impervious');

// 90 m buffer -> a 180 m box. The SAME geometry is passed to all three layers
// per site, so the panels are co-registered even though GEE returns different
// pixel aspect ratios for each. make_figure_matched_parcels.py displays them on a common
// 180 m extent with aspect='equal', which restores true 1:1 geometry.
function box(s) { return ee.Geometry.Point([s.lon, s.lat]).buffer(90).bounds(); }

function thumb(img, vis, region) {
  return new Promise(res => {
    img.getThumbURL(Object.assign({}, vis, { region: region, dimensions: 500, format: 'png' }),
      (url, err) => res(err ? { err: String(err) } : url));
  });
}

const urls = {};
for (const k of ['low', 'high']) {
  const g = box(SITES[k]);
  urls[k + '_naip']   = await thumb(naip, { bands: ['R','G','B'], min: 0, max: 255 }, g);
  urls[k + '_canopy'] = await thumb(ch, { bands: ['cover_code'], min: 0, max: 30,
      palette: ['ffffff','e8f3e0','b7dba0','74c476','31a354','006d2c','00441b'] }, g);
  urls[k + '_imp']    = await thumb(imp, { bands: ['impervious'], min: 0, max: 60,
      palette: ['f7f7f7','d9d9d9','bdbdbd','969696','636363','252525'] }, g);
}
console.log(urls);

// VERIFICATION performed when the figure was made: NLCD impervious sampled at
// each centroid returned 38 and 1, matching nevada_canopy_bias_rowlevel.csv
// exactly. Re-run to confirm:
//   imp.reduceRegion({reducer: ee.Reducer.first(),
//     geometry: ee.Geometry.Point([SITES.low.lon, SITES.low.lat]),
//     scale: 30}).evaluate(console.log);
//
// The red 30 m squares in panels (c) and (f) are the true NLCD cells containing
// each centroid, computed by projecting the centroid to EPSG:5070 and flooring
// to the 30 m grid; see make_figure_matched_parcels.py. They are NOT centred squares.
