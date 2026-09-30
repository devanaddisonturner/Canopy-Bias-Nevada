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
// COMPLETE PIPELINE, AS ACTUALLY RUN, 2026-09-27
// Produces nevada_canopy_bias_rowlevel.csv (24,088 rows) from nothing.
//
// HOW TO RUN: open https://code.earthengine.google.com, sign in, open the
// browser developer console (F12), paste this whole file, press Enter.
// It runs in about 12 minutes, most of it Earth Engine sampling.
//
// WHY THE BROWSER AND NOT A SERVER: the Nevada County ArcGIS service and the
// Earth Engine client both have to be reachable from the same place. A cloud
// sandbox is refused by the ArcGIS host (403 on CONNECT), and Earth Engine's
// JavaScript client lives in this page. The browser is the only place both work.
//
// RESULTS THIS PRODUCED (verified twice, once in JS here and once in Python
// from the written CSV):
//   nlcd_impervious ~ canopy + ac + sqft + slope + n100, n = 21,931
//     canopy = -21.8958, HC1 se 0.4262, t = -51.4, R2 = 0.3203
//     spatial block 1 km (G=287) se 1.354 t = -16.2
//     spatial block 2 km (G=124) se 1.993 t = -11.0
//   below_floor ~ same
//     canopy = +0.3113, 2 km se 0.0360, t = 8.7
//   post-2019 placebo, n = 589, on the CONTINUOUS outcome: canopy = -2.45,
//     t = -1.37, against -21.90 in the main sample. Do NOT quote the binary
//     below_floor placebo (-0.0001): that outcome sits near its ceiling in the
//     post-2019 group, so its null is partly mechanical.
// ============================================================================

const PARCEL_SVC = 'https://maps.nevadacountyca.gov/arcgis/rest/services/' +
                   'web_public/Open_Data_Layers_Nevada_County_1/FeatureServer/200';

// Floor area and parcel size only. NEITHER FILTER USES CANOPY, NLCD OR ANY
// remote-sensing input, so selection cannot correlate with the measurement
// error under study, and neither is tenure-related. That is the property the
// design needs. It is NOT statistical independence from canopy: acres
// correlates with canopy at +0.283. An earlier comment here claimed the
// stronger property untested. The consequence is a scope bound (the estimate
// is for sub-half-acre parcels), not a validity problem; see the limitations.
// No improvement-value filter: it removes only 70 of 24,088
// parcels and makes the frame a function of Proposition 13 base-year
// assessment. Stories <= 4 drops ten records with data errors (one says 32).
const WHERE = 'SquareFeetOnRecord >= 400 AND Stories > 0 AND Stories <= 4 ' +
              'AND GISACRES > 0 AND GISACRES <= 0.5';

// Floor1SquareFeet, Floor2SquareFeet, BasementSquareFeet and
// ImprovementsSquareFeet are IN THE SCHEMA BUT ENTIRELY EMPTY. Checked: each
// returns zero records above zero. Floor1SquareFeet would have been the ideal
// footprint field, which is why the floor goes through SquareFeetOnRecord /
// Stories instead.
const FIELDS = 'APN,GISACRES,SquareFeetOnRecord,Stories,VehicleBuildingSquareFeet,' +
               'PorchSquareFeet,YearBuilt,TotalImproveValue,UseCode,RoadSurface';

const PAGE = 2000, SQFT_TO_M2 = 0.092903, EE_CHUNK = 1000;

// ---- 1. PULL THE CENSUS -----------------------------------------------------
// 24,088 parcels in 13 pages. There is no sampling step, and therefore no
// sampling bias. A naive ordered pull once sampled one town (sd lon 0.015
// against 0.4366 for the census) and inflated the canopy coefficient to -37.
function webMercToLonLat(x, y) {
  const lon = x / 20037508.34 * 180;
  let lat = y / 20037508.34 * 180;
  lat = 180 / Math.PI * (2 * Math.atan(Math.exp(lat * Math.PI / 180)) - Math.PI / 2);
  return [lon, lat];
}
async function getJSON(u) {
  const r = await fetch(u);
  if (!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}
async function pullCensus() {
  const total = (await getJSON(PARCEL_SVC + '/query?where=' + encodeURIComponent(WHERE) +
    '&returnCountOnly=true&f=json')).count;
  const rows = [];
  for (let off = 0; off < total; off += PAGE) {
    const d = await getJSON(PARCEL_SVC + '/query?where=' + encodeURIComponent(WHERE) +
      '&outFields=' + encodeURIComponent(FIELDS) +
      '&returnGeometry=false&returnCentroid=true' +
      '&resultOffset=' + off + '&resultRecordCount=' + PAGE + '&f=json');
    for (const f of (d.features || [])) {
      const a = f.attributes, c = f.centroid;
      if (!c) continue;
      const [lon, lat] = webMercToLonLat(c.x, c.y);
      const living = a.SquareFeetOnRecord || 0;
      const garage = a.VehicleBuildingSquareFeet || 0;
      const storeys = Math.max(a.Stories || 1, 1);
      // Stories is REAL here (frame mean 1.545). An earlier design assumed 2,
      // which understated every roof by about 23 percent.
      // Porch is excluded: a wooden deck is not necessarily impervious.
      rows.push({
        apn: a.APN, lon: lon, lat: lat, ac: a.GISACRES, sqft: living,
        storeys: storeys, garage: garage, porch: a.PorchSquareFeet || 0,
        roof_m2: (living / storeys + garage) * SQFT_TO_M2,
        yr: a.YearBuilt ? +String(a.YearBuilt).trim() : null,
        improve: a.TotalImproveValue || 0,
        use: (a.UseCode || '').trim(), road: (a.RoadSurface || '').trim()
      });
    }
    console.log('pulled', rows.length, '/', total);
  }
  return rows;
}

// ---- 2. NLCD PIXEL GRID AND NEIGHBOUR DENSITY -------------------------------
// EPSG:5070 Albers Equal Area CONUS, the NLCD grid. Verified numerically: the
// projection origin (96 W, 23 N) maps to (0, 0); Nevada City maps to
// (-2114076, 2084142); a 10 m offset returns 10 m and lands in the adjacent
// 30 m cell; a 94 m offset lands three cells away.
const R = 6378137, E2 = 0.0066943800229;
const LAT0 = 23 * Math.PI / 180, LON0 = -96 * Math.PI / 180;
const P1 = 29.5 * Math.PI / 180, P2 = 45.5 * Math.PI / 180;
const qq = s => (1 - E2) * (s / (1 - E2 * s * s) -
  (1 / (2 * Math.sqrt(E2))) * Math.log((1 - Math.sqrt(E2) * s) / (1 + Math.sqrt(E2) * s)));
const mm = s => Math.cos(Math.asin(s)) / Math.sqrt(1 - E2 * s * s);
const S1 = Math.sin(P1), S2 = Math.sin(P2), S0 = Math.sin(LAT0);
const NN = (mm(S1) * mm(S1) - mm(S2) * mm(S2)) / (qq(S2) - qq(S1));
const CC = mm(S1) * mm(S1) + NN * qq(S1);
const RHO0 = R * Math.sqrt(CC - NN * qq(S0)) / NN;
function albers(lonD, latD) {
  const la = latD * Math.PI / 180, lo = lonD * Math.PI / 180;
  const rho = R * Math.sqrt(CC - NN * qq(Math.sin(la))) / NN, th = NN * (lo - LON0);
  return [rho * Math.sin(th), RHO0 - rho * Math.cos(th)];
}

function addPixelAndDensity(rows) {
  // The floor must share a denominator with the measurement. NLCD reports on a
  // 900 m2 pixel that contains the neighbours, so the floor sums every recorded
  // roof in that pixel. THIS IS WHY THE CENSUS IS REQUIRED: a sample misses the
  // neighbours whose roofs share the pixel.
  const acc = {};
  rows.forEach(r => {
    const [X, Y] = albers(r.lon, r.lat);
    r.X = X; r.Y = Y;
    r.px = Math.floor(X / 30) + '_' + Math.floor(Y / 30);
    (acc[r.px] = acc[r.px] || {b: 0, a: 0, n: 0});
    acc[r.px].b += r.roof_m2;                                  // living/storeys + garage
    acc[r.px].a += (r.sqft / r.storeys) * SQFT_TO_M2;          // living/storeys only
    acc[r.px].n += 1;
  });
  rows.forEach(r => {
    r.pixel_roof_m2 = acc[r.px].b;
    r.n_bldg_px = acc[r.px].n;
    r.imp_floor_px = 100 * acc[r.px].b / 900;   // headline floor
    r.floorA = 100 * acc[r.px].a / 900;         // conservative, garage excluded
  });
  // Neighbour density: the competing hypothesis. Uhl and Leyk (2019) published
  // built-up underestimation in low-density rural areas, and canopy is
  // collinear with rural, so canopy must be shown to act WITHIN density
  // stratum. Built from the assessor file, so it is canopy-independent.
  [[100, 'n100'], [250, 'n250']].forEach(([Rm, key]) => {
    const cell = {};
    rows.forEach(r => {
      const k = Math.floor(r.X / Rm) + '_' + Math.floor(r.Y / Rm);
      (cell[k] = cell[k] || []).push(r);
    });
    rows.forEach(r => {
      const cx = Math.floor(r.X / Rm), cy = Math.floor(r.Y / Rm);
      let n = 0;
      for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++)
        for (const o of (cell[(cx + dx) + '_' + (cy + dy)] || [])) {
          const ddx = o.X - r.X, ddy = o.Y - r.Y;
          if (ddx * ddx + ddy * ddy <= Rm * Rm) n++;
        }
      r[key] = n - 1;
    });
  });
}

// ---- 3. EARTH ENGINE SAMPLING -----------------------------------------------
function buildStack() {
  const ee = window.ee;
  const county = ee.FeatureCollection('TIGER/2018/Counties')
    .filter(ee.Filter.and(ee.Filter.eq('NAME', 'Nevada'), ee.Filter.eq('STATEFP', '06')));
  const geom = county.geometry();
  const n19 = ee.Image(ee.ImageCollection('USGS/NLCD_RELEASES/2019_REL/NLCD')
    .filter(ee.Filter.eq('system:index', '2019')).first());
  // 2021_REL contains only the 2021 image; a 2001 filter against it returns null.
  const chC = ee.ImageCollection('projects/meta-forest-monitoring-okw37/assets/CanopyHeight')
    .filterBounds(geom);   // filter to bounds BEFORE mosaic, or all 170 global tiles time out
  const chProj = ee.Image(chC.first()).projection();
  const ch = chC.mosaic().unmask(0);   // tested: canopy is NOT masked off-canopy, unmask is belt and braces
  const dwC = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1').filterBounds(geom)
    .filterDate('2019-01-01', '2020-12-31');
  const dwProj = ee.Image(dwC.first()).select('built').projection();
  const wcI = ee.Image(ee.ImageCollection('ESA/WorldCover/v200').first()).select('Map');
  const ghsl = ee.Image(ee.ImageCollection('JRC/GHSL/P2023A/GHS_BUILT_S')
    .filter(ee.Filter.eq('system:index', '2020')).first())
    .select('built_surface').divide(100);   // m2 per 100 m cell, 0 to 10000
  const dem = ee.Image('USGS/3DEP/10m');    // an Image, band 'elevation', 10.31 m

  // reduceResolution WITHOUT reproject. Two traps here, both hit during
  // development:
  //   - a median composite carries NO default projection, so reduceResolution
  //     fails on Dynamic World unless setDefaultProjection comes first;
  //   - an explicit .reproject() forces a county-wide output grid and throws
  //     "Reprojection output too large" on spatially dispersed chunks.
  // Omitting reduceResolution entirely is also wrong: sampleRegions then does
  // nearest-neighbour and returns a BINARY point sample instead of a 30 m
  // canopy fraction.
  const agg = (img, p) => img.setDefaultProjection(p)
    .reduceResolution({reducer: ee.Reducer.mean(), maxPixels: 4096});

  return agg(ch.gte(2), chProj).rename('canopy_h2')
    .addBands(agg(ch.gte(5), chProj).rename('canopy_h5'))
    .addBands(agg(ch, chProj).rename('canopy_ht'))
    .addBands(n19.select('impervious').rename('nlcd_imp'))
    .addBands(n19.select('landcover').gte(21).and(n19.select('landcover').lte(24))
      .multiply(100).rename('nlcd_dev'))
    .addBands(agg(dwC.select('built').median().multiply(100), dwProj).rename('dw'))
    .addBands(agg(wcI.eq(50).multiply(100), wcI.projection()).rename('wc'))
    .addBands(ghsl.rename('ghsl'))
    .addBands(agg(ee.Terrain.slope(dem), dem.projection()).rename('slope'));
  // NOTE: VIDA_COMBINED/USA footprints were tested and REJECTED. A 20 m disc
  // returned 31 overlapping polygons totalling 36,000 m2 against a disc area
  // of 1,257 m2, which is geometrically impossible for clean footprints.
}

async function sampleEE(rows, stack) {
  const ee = window.ee;
  // Sort spatially so each chunk covers a small area. Interactive EE times out
  // near five minutes; 1,000 points takes about 10 to 40 seconds.
  rows.sort((a, b) => (Math.floor(a.Y / 2000) - Math.floor(b.Y / 2000)) || (a.X - b.X));
  const store = {};
  for (let start = 0; start < rows.length; start += EE_CHUNK) {
    const sl = rows.slice(start, start + EE_CHUNK);
    const fc = ee.FeatureCollection(sl.map((r, k) =>
      ee.Feature(ee.Geometry.Point([r.lon, r.lat]), {i: start + k})));
    for (let att = 0; att < 3; att++) {
      try {
        const res = await new Promise((ok, bad) => {
          stack.sampleRegions({collection: fc, properties: ['i'], scale: 30,
            tileScale: 4, geometries: false})
            .evaluate((v, e) => v ? ok(v) : bad(e || 'null'));
        });
        (res.features || []).forEach(x => { store[x.properties.i] = x.properties; });
        break;
      } catch (e) {
        console.warn('chunk', start, 'attempt', att, e);
        await new Promise(r => setTimeout(r, 2000));
      }
    }
    console.log('sampled', Object.keys(store).length, '/', rows.length);
  }
  return store;
}

// ---- 4. JOIN AND WRITE ------------------------------------------------------
function join(rows, store) {
  const D = [];
  rows.forEach((r, i) => {
    const s = store[i];
    if (!s) return;
    D.push(Object.assign({}, r, {
      canopy: s.canopy_h2, canopy5: s.canopy_h5, canopy_ht: s.canopy_ht,
      nlcd: s.nlcd_imp, dev: s.nlcd_dev, dw: s.dw, wc: s.wc, ghsl: s.ghsl,
      slope: s.slope,
      below:       s.nlcd_imp < r.imp_floor_px ? 1 : 0,
      belowA:      s.nlcd_imp < r.floorA       ? 1 : 0,
      zero:        s.nlcd_imp === 0            ? 1 : 0,
      below_dw:    s.dw   < r.imp_floor_px ? 1 : 0,
      below_wc:    s.wc   < r.imp_floor_px ? 1 : 0,
      below_ghsl:  s.ghsl < r.imp_floor_px ? 1 : 0
    }));
  });
  return D;
}

const COLS = ['apn','lon','lat','ac','sqft','storeys','garage','roof_m2','yr','improve',
  'use','road','px','pixel_roof_m2','n_bldg_px','imp_floor_px','floorA','n100','n250',
  'canopy','canopy5','canopy_ht','nlcd','dev','dw','wc','ghsl','slope',
  'below','belowA','zero','below_dw','below_wc','below_ghsl'];

function toCSV(D) {
  const f = v => (v === null || v === undefined || v === '') ? ''
    : (typeof v === 'number' ? (Number.isInteger(v) ? v : +v.toFixed(4))
    : String(v).replace(/[",\n]/g, ' ').trim());
  return [COLS.join(',')].concat(D.map(r => COLS.map(c => f(r[c])).join(','))).join('\n');
}

// ---- RUN --------------------------------------------------------------------
(async () => {
  console.log('1/4 pulling parcel census');
  const rows = await pullCensus();
  console.log('2/4 pixel grid and neighbour density');
  addPixelAndDensity(rows);
  console.log('3/4 Earth Engine sampling, this is the slow part');
  const store = await sampleEE(rows, buildStack());
  console.log('4/4 joining and writing');
  const D = join(rows, store);
  window.__D = D;
  const csv = toCSV(D);
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], {type: 'text/csv'}));
  a.download = 'nevada_canopy_bias_rowlevel.csv';
  document.body.appendChild(a); a.click(); a.remove();
  console.log('done:', D.length, 'rows written. Data also left in window.__D');
})();
