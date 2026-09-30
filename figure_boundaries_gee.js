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
// Nevada County and California outlines for the study-area figure.
// Run in the browser console at code.earthengine.google.com; writes the JSON
// that make_figure_studyarea.py reads as figure_boundaries.json.
const ee = window.ee;
function evalp(o){ return new Promise(r=>o.evaluate((v,e)=>r({v:v,e:e?String(e):null}))); }
function rings(g){                       // flatten any GeoJSON geometry to exterior rings
  const out=[]; const walk=x=>{
    if(!x) return;
    if(x.type==='GeometryCollection'){ (x.geometries||[]).forEach(walk); return; }
    if(x.type==='Polygon'){ out.push(x.coordinates[0]); return; }
    if(x.type==='MultiPolygon'){ x.coordinates.forEach(p=>out.push(p[0])); return; }
  }; walk(g); return out;
}
const nev = ee.FeatureCollection('TIGER/2018/Counties')
  .filter(ee.Filter.and(ee.Filter.eq('NAME','Nevada'), ee.Filter.eq('STATEFP','06')));
const ca  = ee.FeatureCollection('TIGER/2018/States').filter(ee.Filter.eq('NAME','California'));
const a = await evalp(nev.first().geometry().simplify(200));   // 200 m: county shape stays crisp
const b = await evalp(ca.first().geometry().simplify(4000));   // 4 km: ample for an inset
const big = rs => rs.reduce((m,r)=> r.length>m.length?r:m, rs[0]);
const r4 = a => a.map(p=>[Math.round(p[0]*1e4)/1e4, Math.round(p[1]*1e4)/1e4]);  // ~11 m
console.log(JSON.stringify({
  source: 'TIGER/2018/Counties and TIGER/2018/States via Google Earth Engine; simplify 200 m and 4 km',
  nevada: r4(big(rings(a.v))),
  california: r4(big(rings(b.v)))
}));
// Note: the county geometry returns as a GeometryCollection, not a Polygon,
// which is why rings() walks the structure rather than reading .coordinates.
