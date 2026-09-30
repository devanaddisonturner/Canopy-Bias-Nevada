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
// verify_support.js
//
// Settles two open questions about the released dataset, in one run, without
// modifying or re-exporting anything. Paste into the Earth Engine Code Editor
// (code.earthengine.google.com) and press Run. It only prints.
//
//   Q1. Is the 30 m cell that the bound is summed over the SAME cell that NLCD
//       reports? `px` is built by projecting the centroid to EPSG:5070 and
//       flooring to a 30 m lattice anchored at the projection origin. NLCD's
//       own grid is anchored at its product corner, which need not fall on that
//       lattice. A constant offset would mean the bound's denominator and the
//       reported pixel are neighbouring cells for parcels near a boundary.
//
//   Q2. What spatial support do the released covariates use? The manuscript
//       says every layer is "aggregated to the 30 m analysis grid ... and
//       sampled at parcel centroids". canopy_bias_extraction.js buffers each
//       centroid by 20 m and takes a mean, which is a 1,257 m2 disc rather than
//       a 900 m2 cell.
//
// Local evidence already settles the NLCD outcome: decoding the exported
// Figure 3 rasters gives the centre pixel as 37.9 and 0.8 against released
// values of 38 and 1, where a 20 m disc would give 22.6 and 10.6. So `nlcd` is
// the pixel value. The canopy layers could not be settled the same way, because
// the rendered canopy thumbnail decodes too coarsely: the canopied site reads
// 0.84 to 0.88 cover where the released value is exactly 1.0000.
// ============================================================================

var imp = ee.Image('USGS/NLCD_RELEASES/2019_REL/NLCD/2019').select('impervious');
var ch  = ee.ImageCollection('projects/meta-forest-monitoring-okw37/assets/CanopyHeight')
            .mosaic().unmask(0);

// ---- Q1. NLCD's grid, against the lattice `px` is built on -----------------
// crs_transform is [xScale, xShear, xOrigin, yShear, yScale, yOrigin].
// If xOrigin and yOrigin are exact multiples of 30, the two lattices coincide
// and `px` is the NLCD pixel. If not, the printed remainders are the offset.
imp.projection().getInfo(function (p) {
  var tr = p.transform;
  print('NLCD projection', p.crs, 'transform', tr);
  print('x origin mod 30 (0 means the grids coincide)', tr[2] % 30);
  print('y origin mod 30 (0 means the grids coincide)', tr[5] % 30);
});

// ---- Q2. Pixel value against disc mean, at the two illustrated parcels -----
// Released values, from nevada_canopy_bias_rowlevel.csv:
//   040-050-027  nlcd 38  canopy 0.0419
//   045-300-033  nlcd  1  canopy 1.0000
var SITES = [
  {apn: '040-050-027', lon: -120.09190, lat: 39.35480, nlcd: 38, canopy: 0.0419},
  {apn: '045-300-033', lon: -120.20670, lat: 39.34660, nlcd: 1,  canopy: 1.0000}
];

SITES.forEach(function (s) {
  var pt = ee.Geometry.Point([s.lon, s.lat]);
  var cover = ch.gte(2);

  // the single pixel containing the centroid
  var impPixel = imp.reduceRegion({reducer: ee.Reducer.first(), geometry: pt, scale: 30});
  // the mean over the 20 m disc the extraction script uses
  var impDisc  = imp.reduceRegion({reducer: ee.Reducer.mean(),
                                   geometry: pt.buffer(20), scale: 10, maxPixels: 1e9});
  // canopy cover above 2 m, on each candidate support
  var canDisc  = cover.reduceRegion({reducer: ee.Reducer.mean(),
                                     geometry: pt.buffer(20), scale: 1, maxPixels: 1e9});
  var canCell  = cover.reduceRegion({reducer: ee.Reducer.mean(),
                                     geometry: pt.buffer(15).bounds(), scale: 1, maxPixels: 1e9});

  print('---- ' + s.apn + ' ----');
  print('released nlcd ' + s.nlcd + ' | pixel', impPixel, '| 20 m disc', impDisc);
  print('released canopy ' + s.canopy + ' | 20 m disc', canDisc, '| ~30 m cell', canCell);
});

// ============================================================================
// Reading the result
//
// Q1. Both remainders zero  -> `px` is the NLCD pixel; the bound and the
//     product share a denominator exactly, as Section 2.2 states. Non-zero ->
//     the two lattices are offset by that amount, and the shared-denominator
//     claim holds only for parcels far enough from a cell boundary.
//
// Q2. If released canopy matches the 20 m disc, Section 2.3's sentence needs
//     restating: the canopy layers, the three comparison products and the
//     terrain covariates are means over a 20 m radius disc centred on the
//     parcel centroid, not values on the 30 m analysis grid. NLCD itself is
//     described correctly either way.
// ============================================================================
