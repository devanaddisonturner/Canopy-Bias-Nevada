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
// Code MIT, released data CC0 1.0.
// ---------------------------------------------------------------------------
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, PageOrientation,
  Footer, PageNumber, ImageRun, Tab, TabStopType
} = require('docx');
const fs = require('fs');
const path = require('path');
const HERE = __dirname;

// Read a PNG's pixel dimensions from its IHDR chunk, so an embedded figure can
// never be stretched by a stale hard-coded height.
function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
function figFit(file, widthPx) {
  const { w, h } = pngSize(file);
  return { width: widthPx, height: Math.round(widthPx * h / w) };
}



const FONT = 'Times New Roman';
const SZ = 24;      // 12pt half-points: body and references
const SZ_SM = 24;   // 12pt: references match the body
const SZ_TBL = 24;  // table cells and captions
const LINE = 276;   // ~1.15 spacing

// Bold every in-text callout to a table or figure, and the caption label.
const CALLOUT = /\b(Tables?\s\d+(?:\s(?:and|to|through)\s\d+)?|Figures?\s\d+|Equations?\s\d+(?:\s(?:and|to|through)\s\d+)?)\b/g;
// Applied at render time only, so the source strings keep ordinary spaces and
// every verification lint that searches them keeps working. Binds a value to a
// unit symbol and a cross-reference label to its number, so neither is split
// across a line break: "above 2 m" and "Section 3.5" were both broken.
function nbsp(text) {
  return text
    .replace(/(\d)\s(m|km|ha|mm)\b/g, '$1\u00a0$2')
    .replace(/\b(Figures?|Tables?|Sections?|Equations?)\s(\d)/g, '$1\u00a0$2');
}

function runsFor(text, size, bold, italics) {
  text = nbsp(text);
  const out = []; let last = 0, m;
  CALLOUT.lastIndex = 0;
  while ((m = CALLOUT.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), font: FONT, size, bold: !!bold, italics: !!italics }));
    out.push(new TextRun({ text: m[0], font: FONT, size, bold: true, italics: !!italics }));
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), font: FONT, size, bold: !!bold, italics: !!italics }));
  return out.length ? out : [new TextRun({ text, font: FONT, size, bold: !!bold, italics: !!italics })];
}

function p(text, opts = {}) {
  const {
    bold = false, italics = false, size = SZ, align = AlignmentType.JUSTIFIED,
    before = 0, after = 100, indent = null, keepNext = false
  } = opts;
  return new Paragraph({
    alignment: align,
    spacing: { line: LINE, before, after },
    keepNext,
    indent,
    children: runsFor(text, size, bold, italics)
  });
}

// paragraph with mixed runs: pass array of {t, b, i}
function pr(runs, opts = {}) {
  const { align = AlignmentType.JUSTIFIED, size = SZ, before = 0, after = 100, keepNext = false } = opts;
  return new Paragraph({
    alignment: align,
    spacing: { line: LINE, before, after },
    keepNext,
    children: runs.map(r => new TextRun({
      text: r.t, font: FONT, size: r.size || size, bold: !!r.b, italics: !!r.i
    }))
  });
}

// ---------------------------------------------------------------- equations
// A display equation: centred on a centre tab, with its number right-aligned at
// the margin. Runs are {t, i (italic), sub, sup}; the number is added by the
// caller's position in EQN order so the text and the display can never disagree.
const TEXT_W = 9360;   // 12240 page - 1440 left - 1440 right, in DXA
function eq(runs, number) {
  const kids = [new TextRun({ children: [new Tab()] })];
  for (const r of runs) {
    kids.push(new TextRun({
      text: r.t, font: FONT, size: SZ,
      italics: !!r.i, subScript: !!r.sub, superScript: !!r.sup
    }));
  }
  kids.push(new TextRun({ children: [new Tab()], font: FONT, size: SZ }));
  kids.push(new TextRun({ text: '(' + number + ')', font: FONT, size: SZ }));
  return new Paragraph({
    spacing: { line: LINE, before: 120, after: 120 },
    tabStops: [
      { type: TabStopType.CENTER, position: Math.round(TEXT_W / 2) },
      { type: TabStopType.RIGHT,  position: TEXT_W }
    ],
    children: kids
  });
}

// the "where" line under an equation: italic symbols, roman prose
function where(runs) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: LINE, before: 0, after: 100 },
    // A plain run here is ordinary prose and may contain a cross-reference, so
    // it goes through runsFor for the same bolding the body text gets. Runs
    // carrying a symbol flag are set literally.
    children: runs.flatMap(r => (r.i || r.sub || r.sup)
      ? [new TextRun({ text: r.t, font: FONT, size: SZ,
          italics: !!r.i, subScript: !!r.sub, superScript: !!r.sup })]
      : runsFor(r.t, SZ, false, false))
  });
}

function h1(text) {
  return new Paragraph({
    spacing: { line: LINE, before: 200, after: 80 },
    keepNext: true,
    children: [new TextRun({ text, font: FONT, size: SZ, bold: true })]
  });
}

function h2(text) {
  return new Paragraph({
    spacing: { line: LINE, before: 140, after: 60 },
    keepNext: true,
    children: [new TextRun({ text, font: FONT, size: SZ, bold: true, italics: true })]
  });
}

function caption(text) {
  const lbl = text.match(/^((?:Table|Figure)\s\d+\.)\s*/);
  const kids = lbl
    ? [new TextRun({ text: lbl[1] + ' ', font: FONT, size: SZ_TBL, bold: true })]
        .concat(runsFor(text.slice(lbl[0].length), SZ_TBL, false, false))
    : runsFor(text, SZ_TBL, false, false);
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: LINE, before: 140, after: 60 },
    keepNext: true,
    children: kids
  });
}

function note(text) {
  return new Paragraph({
    spacing: { line: LINE, before: 40, after: 140 },
    children: [new TextRun({ text, font: FONT, size: SZ_SM, italics: true })]
  });
}

const TOTAL_W = 9360; // 6.5in usable width in DXA

function makeTable(rows, widths, opts = {}) {
  const { headerRows = 1, alignCols = null } = opts;
  const sum = widths.reduce((a, b) => a + b, 0);
  const cw = widths.map(w => Math.round(w / sum * TOTAL_W));
  const diff = TOTAL_W - cw.reduce((a, b) => a + b, 0);
  cw[0] += diff;

  // Booktabs convention: a rule above the header, a rule below the header,
  // a rule at the foot of the table, and nothing at all between cells.
  const NO_BORDER = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
  const headCellBorders = {
    top: NO_BORDER, left: NO_BORDER, right: NO_BORDER,
    bottom: { style: BorderStyle.SINGLE, size: 4, color: '000000' }
  };
  const bodyCellBorders = {
    top: NO_BORDER, bottom: NO_BORDER, left: NO_BORDER, right: NO_BORDER
  };

  // Keep every table whole on one page: cantSplit stops a single row breaking
  // across a page, and keepNext on every row but the last pulls the whole
  // table to the next page rather than letting it straddle a break.
  //
  // tableHeader is set on the header rows as well, as insurance. An earlier
  // comment here claimed the flag would produce a duplicate header. That is
  // wrong: w:tblHeader marks a row to repeat at the top of a CONTINUATION
  // page, and has no effect at all on a table that does not span one. So it
  // costs nothing today and protects the reader if later edits, such as
  // filling the remaining placeholders, push a table across a break.
  const lastRow = rows.length - 1;
  const trs = rows.map((cells, ri) => {
    const isHead = ri < headerRows;
    return new TableRow({
      cantSplit: true,
      // Spread conditionally: docx-js emits <w:tblHeader/> whenever the key is
      // present, even when its value is false, which would mark every body row
      // as a header and repeat the whole table on a split.
      ...(isHead ? { tableHeader: true } : {}),
      children: cells.map((c, ci) => new TableCell({
        width: { size: cw[ci], type: WidthType.DXA },
        borders: isHead ? headCellBorders : bodyCellBorders,
        margins: { top: 60, bottom: 60, left: 80, right: 80 },
        children: [new Paragraph({
          spacing: { line: 240, before: 0, after: 0 },
          keepNext: ri < lastRow,
          // Header cells are centred in every column, including column 0 and
          // any column carrying an alignCols override, which applies to the
          // body cells only.
          alignment: isHead ? AlignmentType.CENTER
            : (alignCols && alignCols[ci]) ? alignCols[ci]
            : (ci === 0 ? AlignmentType.LEFT : AlignmentType.CENTER),
          children: [new TextRun({ text: String(c), font: FONT, size: SZ_TBL, bold: isHead })]
        })]
      }))
    });
  });

  return new Table({
    columnWidths: cw,
    width: { size: TOTAL_W, type: WidthType.DXA },
    rows: trs,
    borders: {
      top:    { style: BorderStyle.SINGLE, size: 4, color: '000000' },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: '000000' },
      left:   NO_BORDER,
      right:  NO_BORDER,
      insideHorizontal: NO_BORDER,
      insideVertical:   NO_BORDER
    }
  });
}

const body = [];

// ============================== TITLE PAGE ==============================
body.push(new Paragraph({
  alignment: AlignmentType.LEFT,
  spacing: { line: LINE, after: 160 },
  children: [new TextRun({
    text: 'An optically independent administrative reference for validating built-surface products, and the tree-canopy bias it reveals',
    font: FONT, size: 28, bold: true
  })]
}));

body.push(pr([{ t: 'Devan Cantrell Addison-Turner' }], { align: AlignmentType.LEFT, after: 40 }));
body.push(pr([{ t: 'Department of Civil and Environmental Engineering, Stanford University, Stanford, CA, USA', i: true, size: SZ_SM }], { align: AlignmentType.LEFT, after: 40 }));
body.push(pr([{ t: 'Corresponding author: daddisonturner@stanford.edu', size: SZ_SM }], { align: AlignmentType.LEFT, after: 40 }));
body.push(pr([{ t: 'ORCID: 0000-0002-2511-3680', size: SZ_SM }], { align: AlignmentType.LEFT, after: 240 }));

// ============================== ABSTRACT ==============================
body.push(h1('Abstract'));
body.push(p('Percentage impervious surface from optical satellite products underpins stormwater regulation, land-change accounting and equity assessment, yet it is validated almost exclusively against other optical references. Any error mechanism that suppresses the built signal in the reference as well as in the product is therefore invisible by construction, and tree canopy is the obvious candidate. This paper contributes a validation reference that does not share that blind spot. Assessor floor area divided by storey count, summed over the parcels in a raster cell, gives a lower bound on the impervious fraction that cell holds. The bound is exact where the recorded roof falls wholly inside the cell, which is 35.2 percent of parcels, and holds in aggregate otherwise. It uses no optical input, so it cannot inherit optical occlusion, and it turns disagreement into a testable claim about named cells. The frame is 24,088 parcels under half an acre in Nevada County, California, each carrying a recorded dwelling, of which 21,931 predate the product epoch. Across four products, closed canopy is associated with 18 to 22 percentage points less measured National Land Cover Database (NLCD) impervious surface than open ground, and a 31 point higher probability of falling below the bound. The association holds within every settlement-density quartile of the frame, survives conditioning on the bound itself, and holds on the subset where the bound is exact. The reference is validated against an independent building-footprint product: where canopy is absent the median ratio of detected footprint to recorded roof is 1.01, and under closed canopy 0.54, so a different sensor and vendor reproduce the same gradient. Loss of built signal ranges from 98 percent for a hard land-cover class to 41 percent for a built-area estimate, though decision rule is confounded with resolution, sensor and epoch. Parcels built after the product epoch serve as a negative control, returning minus 2.45 against minus 21.90. The method needs only a parcel roll carrying floor area and storey count, which is a weaker requirement than imagery though not a universal one.',
  { align: AlignmentType.JUSTIFIED, after: 160 }));

body.push(pr([{ t: 'Keywords: ', b: true },
  { t: 'impervious surface; accuracy assessment; tree canopy; cadastral and assessor data; NLCD; validation reference' }],
  { after: 240 }));

// ============================== 1. INTRODUCTION ==============================
body.push(h1('1. Introduction'));

body.push(p('Percentage impervious surface is among the most consequential quantities derived from moderate-resolution satellite imagery. It sets runoff coefficients and curve numbers, and with them stormwater utility fees. Regulators use it as a surrogate target for total maximum daily loads under Clean Water Act Section 303(d), where impairment thresholds sit near 10 to 12 percent impervious cover (US EPA 2015; Connecticut DEP 2006). National land-change accounting depends on it, and environmental-equity assessment has recently adopted it as a distributional indicator (Culler et al. 2024). The National Land Cover Database (NLCD) percentage developed impervious layer is the dominant United States source (Yang et al. 2018; Dewitz 2021).'));

body.push(p('Its validation history is thin and methodologically uniform. Nowak and Greenfield (2010) compared NLCD impervious and canopy estimates against photointerpreted points across all 65 mapping zones and found national underestimation of 1.4 percentage points (standard error 0.4), rising to 5.2 points within developed land with a standard error of 4.8, leaving that magnitude open. Wickham et al. (2020) assessed NLCD2011 percentage impervious against 1 m EnviroAtlas land cover for 18 metropolitan areas, reporting a tendency to underestimate outside highly urbanised cores, with 1st and 99th percentile deviations of minus 29.2 and plus 25.3 points at the 1 ha assessment unit, narrowing as the unit grows. The NLCD program’s own current assessment states that the impervious and canopy components have been evaluated only by researchers outside the program (Wickham et al. 2026), and the thematic assessments address land-cover classes rather than the sub-pixel impervious fraction (Wickham et al. 2021, 2023).'));

body.push(p('Every one of those references is ultimately optical. Photointerpretation and high-resolution orthoimagery observe the surface from above and share the occlusion they would be used to detect. Airborne lidar is the partial exception, since multiple returns can recover structure beneath a broken canopy, but lidar references are not available at national scale for the products assessed here and were not used to validate any of them. The strongest available candidate for a reference of this kind is the 1 m EnviroAtlas meter-scale urban land cover used by Wickham et al. (2020), which is derived chiefly from aerial imagery with lidar as ancillary data and covers 30 communities delineated from census urban areas (Pilant et al. 2020). It cannot serve here on either count: a foothill county falls outside that frame by construction, and its primary input is the viewpoint whose limits are at issue. Building-footprint products fail on the same count, being imagery-derived: Section 3.6 finds one detecting no building in 30.6 percent of cells in the two highest canopy deciles. Where a structure is hidden, an instruction to interpreters to look beneath the canopy is limited by whether anything beneath the canopy is visible. The consequence is structural rather than accidental: an error mechanism that suppresses the built signal in both the product and its reference cannot be detected by comparing them. Tree canopy is the most plausible such mechanism, and no published accuracy assessment of these products appears to use canopy cover as the conditioning variable. The field stratifies by settlement density and by land-cover class.'));

body.push(p('Density matters here for a second reason. Uhl et al. (2020) compared Global Human Settlement Layer built-up products against cadastral parcel and building-footprint references and found substantial underestimation in the rural stratum. Canopy cover and rurality are collinear. A finding that canopy predicts under-detection is therefore not separable, on that evidence alone, from a result already in the literature.'));

body.push(p('This paper makes a methodological contribution and uses it to settle that question. The contribution is a validation reference for built-surface products that is constructed from administrative property records rather than imagery, and that is therefore independent of the optical measurement process under test. Property records have been used to build settlement data at national scale (Leyk and Uhl 2018; Uhl et al. 2021) and as reference data for areal comparison (Uhl et al. 2020). What has not been done is to use them to construct a physical lower bound: a minimum impervious fraction that a raster cell provably contains, which the product either reports or fails to report. That replaces a comparison of two estimates with a testable claim about a specific cell, and it makes the error mechanism addressable.'));

// ============================== 2. METHODS ==============================
body.push(h1('2. Materials and methods'));

body.push(h2('2.1. Study area and parcel frame'));
body.push(p('Nevada County, California, is a Sierra Nevada foothill county with dense conifer forest over dispersed residential development. That makes canopy variation large and largely independent of wealth. On the 21,852 of the 21,931 analysed parcels that carry a recorded improvement value, canopy correlates with that value at minus 0.054, and mean canopy runs from 0.448 to 0.427 across improvement-value quintiles. The county holds 101,911 residents in 55,074 housing units, median household income $89,882 and median owner-occupied home value $621,800 (US Census Bureau 2025). It publishes an ArcGIS REST parcel service, which on 26 September 2026 carried 64,401 records with floor area, storey count, garage area, parcel area, year built and road surface. Figure 1 shows the analysed parcels and their canopy.'));

body.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 160, after: 80 },
  keepNext: true,
  children: [new ImageRun({ type: 'png',
    altText: { name: 'Figure 1. Study area', title: 'Figure 1. Study area', description: 'Map of Nevada County, California, showing the 21,931 analysed parcels coloured by canopy cover above 2 m on a scale from 0 to 1. Settlement is clustered rather than dispersed: five of 47 occupied 5 km grid cells hold 50 percent of the parcels. An inset locates the county within California, and a scale bar and north arrow are shown.' },
    data: fs.readFileSync(path.join(HERE, 'figure_studyarea.png')),
    transformation: figFit(path.join(HERE, 'figure_studyarea.png'), 624) })]
}));
body.push(caption('Figure 1. Study area. Nevada County, California, with the 21,931 analysed parcels coloured by canopy cover above 2 m, and the two parcels of Figure 3 circled. Settlement is clustered rather than dispersed: five of 47 occupied 5 km cells hold 50 percent of the parcels, which is why spatially robust standard errors are reported throughout. County and state outlines are Topologically Integrated Geographic Encoding and Referencing (TIGER) 2018 via Google Earth Engine. Geographic coordinates, World Geodetic System 1984 (WGS 84); the vertical exaggeration is set so that the county is drawn in true local proportion at this latitude. North is up.'));

body.push(p('The analytical frame is defined by two attributes only, recorded floor area of at least 400 square feet and parcel area greater than zero and at most 0.5 acres, plus a storey count between one and four that removes ten records with evident data errors. Storey count is recorded as an integer, so a dwelling with a half storey is coded to one value or the other. Where it is rounded down, the divisor is too small and the footprint too large. This is the one input that could push the bound above what a cell must hold, which is why the straddle and truncation checks below matter. Neither filter uses canopy, imagery or any remote-sensing input. That is weaker than statistical independence from canopy, which does not hold: parcel area correlates with canopy at plus 0.283, so the frame is not a random slice of the county. The consequence is a bound on scope rather than on validity and is addressed in Section 4. No filter on assessed value is applied, because that would make the frame a function of ownership tenure through California Proposition 13 base-year assessment.'));

body.push(p('The frame contains 24,088 parcels. Parcels built on or before 2019 form the analysis sample (n = 21,931) and parcels built after the product epoch form a negative control (n = 589); 1,568 records carry no year built and are excluded from both. The analysis sample is 39.8 percent of the county’s housing units and, at 2.36 persons per household, houses on the order of half its residents. Every parcel carries a recorded dwelling, which is the property the bound requires: the assessor records at least one dwelling unit on 24,021 of the 24,088 and zero units on none, 67 leaving the field blank, and a bedroom or bathroom count on 99.8 percent. The frame is thus residential in the sense that a habitable structure is on the roll, and it is not defined by use code. One code covers 86.8 percent of them. Next largest, at 7.1 percent of the sample, is a group with a median lot of 0.02 acres, one dwelling unit and 2.2 bedrooms apiece, which is the signature of condominium units rather than of non-residential land. Section 3.6 reports the result with these removed.'));

body.push(p('The frame is otherwise structurally homogeneous: 50.5 percent of dwellings are single-storey and 46.3 percent two-storey, the median is 1,652 square feet on 0.30 acres built in 1984, and 81.8 percent have an attached garage averaging 531 square feet. The structures occupy 18,102 distinct 30 m cells, 83 percent of which hold exactly one parcel, and those cells hold 68 percent of the parcels.'));


body.push(h2('2.2. An optically independent lower bound'));
body.push(p('For each parcel, the ground footprint of the recorded structure is the recorded floor area divided by the storey count, plus the recorded attached-garage area. Both are roofed. Garages are recorded for 82 percent of parcels and average 531 square feet, so omitting them would lower the mean bound from 25.1 to 19.2 percent of cell area and the breach rate from 58.8 to 49.8 percent. Including them raises the bar the product must clear and also lowers the estimated effect, from the plus 0.3236 that excluding them gives to the plus 0.3119 reported here, so it is the conservative choice. The county records a ground-floor area field that would give the footprint directly, but it is unpopulated throughout the frame. Equation 1 states it.'));

body.push(p('Footprints are then summed over all parcels whose centroid falls within a 30 m cell of the NLCD Albers grid (EPSG:5070, cell area 900 square metres), and that sum as a percentage of cell area is the bound. Because a cell cannot be more than wholly impervious, the bound is truncated at 100 percent, which is Equation 2. Truncation binds on 163 parcels in 33 cells, 0.74 percent of the sample. These are the extreme case of the centroid rule discussed below, where a structure larger than a whole cell is charged to the one holding its centroid. Those cells average 0.05 canopy, so the correction falls in the open, and it slightly steepens the gradient reported below rather than flattening it. Figure 2 sets out the construction. Two outcomes follow: the measured impervious percentage, and a binary indicator that the product reports less than the bound, which is a detection failure rather than a disagreement. Equation 3 defines the second.'));

// --- Equations 1 and 2: the footprint, and the truncated cell bound
body.push(eq([
  { t: 'a', i: true }, { t: 'i', i: true, sub: true },
  { t: ' = ( ' },
  { t: 'F', i: true }, { t: 'i', i: true, sub: true },
  { t: ' / ' },
  { t: 's', i: true }, { t: 'i', i: true, sub: true },
  { t: ' + ' },
  { t: 'g', i: true }, { t: 'i', i: true, sub: true },
  { t: ' ) \u00d7 ' }, { t: '\u03ba', i: true }
], 1));
body.push(where([
  { t: 'where ' },
  { t: 'a', i: true }, { t: 'i', i: true, sub: true },
  { t: ' is the roofed ground area of parcel ' }, { t: 'i', i: true },
  { t: ' in square metres, ' },
  { t: 'F', i: true }, { t: 'i', i: true, sub: true },
  { t: ' its recorded floor area and ' },
  { t: 's', i: true }, { t: 'i', i: true, sub: true },
  { t: ' its storey count, ' },
  { t: 'g', i: true }, { t: 'i', i: true, sub: true },
  { t: ' its recorded attached-garage area, and ' }, { t: '\u03ba', i: true },
  { t: ' = 0.092903 square metres per square foot. '
       + 'Both terms are recorded without reference to any image. Equation 1 is '
       + 'introduced here. Its input, assessor-reported gross indoor floor area, is the same quantity '
       + 'from which the HISDAC-US built-up intensity layer is constructed (Leyk and Uhl 2018; Uhl et al. '
       + '2021); the division by storey count to recover a ground footprint, and the addition of the '
       + 'recorded garage, are this paper\u2019s.' }
]));

body.push(eq([
  { t: 'B', i: true }, { t: 'c', i: true, sub: true },
  { t: ' = min \u007b 100 \u00d7 ( \u03a3' },
  { t: 'i', i: true, sub: true }, { t: ' \u2208 ', sub: true }, { t: 'c', i: true, sub: true },
  { t: ' ' }, { t: 'a', i: true }, { t: 'i', i: true, sub: true },
  { t: ' ) / ' }, { t: 'A', i: true }, { t: ' , 100 \u007d' }
], 2));
body.push(where([
  { t: 'where ' },
  { t: 'B', i: true }, { t: 'c', i: true, sub: true },
  { t: ' is the bound for cell ' }, { t: 'c', i: true },
  { t: ' as a percentage of its area, the sum runs over every parcel whose centroid falls in that cell, and ' },
  { t: 'A', i: true },
  { t: ' = 900 square metres. The outer minimum imposes the physical ceiling: no cell can be more than '
       + 'wholly impervious. Equation 2 is introduced here. The grid is the NLCD Albers projection '
       + '(Dewitz 2021); nothing else in it is borrowed.' }
]));

body.push(p('Two properties of Equation 2 need stating plainly. The ceiling is the easy one. The harder one is that footprints are assigned by parcel centroid, so a roof lying near a cell edge is charged in full to the cell holding the centroid while part of it physically sits in the neighbour. Every centroid was projected into EPSG:5070 and its distance to the nearest cell edge compared against the roof\u2019s linear extent. The median roof side is 12.5 m against a median edge distance of 4.4 m. Only 35.2 percent of parcels therefore have a roof provably contained in the cell it is charged to. For those the bound is exact in the sense the word implies; for the remainder it is a bound in aggregate rather than cell by cell, because roofs charged out of a cell are offset in expectation by roofs charged into it. The language of proof is used below only where it is earned.'));

body.push(p('The reference itself is validated against an independent building-footprint product in Section 3.6. The direction of the residual error is known: charging a straddling roof in full inflates that cell\u2019s bound and therefore the breach rate, which is part of why 43.7 percent of parcels breach even in the lowest canopy decile. Section 3.6 reports the result on the subset where the bound is exact, and the canopy gradient there is steeper rather than weaker.'));
// --- Equation 3: the detection-failure indicator
body.push(eq([
  { t: 'D', i: true }, { t: 'c', i: true, sub: true },
  { t: ' = 1[ ' },
  { t: 'P', i: true }, { t: 'c', i: true, sub: true },
  { t: ' < ' },
  { t: 'B', i: true }, { t: 'c', i: true, sub: true },
  { t: ' ]' }
], 3));
body.push(where([
  { t: 'where ' }, { t: 'P', i: true }, { t: 'c', i: true, sub: true },
  { t: ' is the impervious percentage the product reports for cell ' }, { t: 'c', i: true },
  { t: ' and 1[\u00b7] is the indicator function. ' },
  { t: 'D', i: true }, { t: 'c', i: true, sub: true },
  { t: ' = 1 marks a cell where the product reports less impervious surface than the recorded structures '
       + 'occupy. Rates are reported per parcel throughout: a parcel counts as a detection failure when the cell containing it breaches, so a cell holding several parcels contributes once for each. Per cell the headline rate is 56.9 rather than 58.8 percent. The indicator form is standard; what is introduced here is the use of an administrative lower bound, rather than a second optical reference, as the quantity on its right-hand side.' }
]));


body.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 160, after: 80 },
  keepNext: true,
  children: [new ImageRun({ type: 'png',
    altText: { name: 'Figure 2. Construction of the bound', title: 'Figure 2. Construction of the bound', description: 'A four-panel flow diagram showing how the physical bound is built from assessor records without using imagery. Panel 1 gives the assessor record for one parcel: 1,470 square feet of floor area, one storey, a 725 square foot attached garage, built in 1998. Panel 2 divides floor area by storey count and adds the garage to give 204 square metres of roofed ground. Panel 3 places that footprint in a 30 m cell of 900 square metres, where it is 22.7 percent of the cell. Panel 4 compares the bound of 22.7 percent against the 1 percent NLCD reports, leaving 21.7 percentage points unaccounted.' },
    data: fs.readFileSync(path.join(HERE, 'figure_schematic.png')),
    transformation: figFit(path.join(HERE, 'figure_schematic.png'), 624) })]
}));
body.push(caption('Figure 2. Construction of the bound. Equations 1 and 2 are applied to the canopied parcel of Figure 3 (assessor parcel number, APN, 045-300-033). Recorded floor area divided by storey count, plus the recorded attached garage, gives the roofed ground the structure must occupy. Footprints are summed over every parcel assigned to the 30 m cell and expressed as a percentage of its 900 square metres. No step uses imagery, so the bound cannot inherit the occlusion it is used to detect. Here the bound is 22.7 percent and NLCD reports 1 percent. In panel 3 the roof is drawn at its true share of the cell area; its position within the cell is illustrative, since the method uses area alone and not where the structure sits.'));

body.push(p('The bound is conservative in three respects, all working against the finding, and the first is large enough to quantify. It counts the dwelling and its attached garage only. Excluded are the driveways, walkways and patios every parcel possesses, and two structures the assessor records separately: porch and deck area, present on 55.4 percent of the sample and averaging 994 square feet where present, and guest houses on a further 47 parcels. Together these are 112.5 hectares of recorded roof, 32.0 percent of the roof area counted. Adding them raises the mean bound from 25.1 to 32.3 percent and the breach rate from 58.8 to 68.2 percent. Scaling 25.1 by 32.0 percent would give 33.2 rather than 32.3, because that percentage is a ratio of total roofed area in the analysis sample while the bound is summed per cell over the whole frame, and the ceiling then binds on 108 cells. The porch-inclusive specification leaves the canopy coefficient on detection failure at plus 0.269, Conley t of plus 7.5. The reported specification is thus conservative by a wide and measured margin.'));

body.push(p('Second, the bound is computed on the full cell, so the whole footprint of every structure assigned to a cell is charged against that cell’s 900 square metres. Third, it is mechanically lower where canopy is higher, because fewer buildings share a cell: canopy correlates with the per-cell building count at minus 0.211 and with the bound at minus 0.267. High-canopy cells face a lower bar and fail it more often regardless.'));

body.push(p('A third outcome requires no roof arithmetic. A product reporting exactly zero impervious surface at a cell holding a recorded, assessed dwelling is an error under any assumption about footprint geometry, and is the assumption-free variant.'));


body.push(h2('2.3. Earth observation products and canopy'));
body.push(p('Four products spanning four decision rules are evaluated. NLCD 2019 percentage developed impervious is a continuous sub-pixel fraction. Dynamic World built probability is a per-pixel class probability (Brown et al. 2022), European Space Agency (ESA) WorldCover built-up is a hard land-cover class (Zanaga et al. 2022), and Global Human Settlement Layer (GHSL) built surface is a built area per cell (Pesaresi et al. 2024). Canopy comes from the Meta and World Resources Institute (WRI) canopy-height model at approximately 1.19 m (Tolan et al. 2024), reduced to cover fractions above 2 m and above 5 m and to mean height. Terrain slope and elevation come from the United States Geological Survey (USGS) 3D Elevation Program (3DEP) 10 m digital elevation model, and Visible Infrared Imaging Radiometer Suite (VIIRS) 2016 and Defense Meteorological Satellite Program (DMSP) 2011 nighttime radiance are included for the reason given in Section 3.5. All layers are aggregated to the 30 m analysis grid in Google Earth Engine by area-weighted mean with an explicit default projection, and sampled at parcel centroids.'));

body.push(p('The epochs differ and are stated because the design depends on them: NLCD is the 2019 release, Dynamic World a median composite over 2019 and 2020, WorldCover v200 is 2021, and GHSL is the 2020 epoch of release P2023A. Every parcel in the analysis sample was built on or before 2019 and so predates all four, which is what makes the cross-product comparison fair. The negative control is reported on the NLCD outcome alone, whose epoch is 2019; 242 of its 589 parcels were built in 2020 or 2021 and would be visible to the later products, so the control does not transfer to them. Settlement density is built from the assessor file rather than from imagery, as counts of other qualifying parcels within 100 m and 250 m. This matters: the density covariate must not inherit the optical error whose separation from density is the point of the test.'));

body.push(h2('2.4. Estimation and inference'));
body.push(p('All specifications take the form of Equation 4, regressing an outcome on canopy fraction above 2 m with parcel area, recorded floor area, terrain slope and neighbour count within 100 m as covariates. Because parcels are spatially clustered, heteroskedasticity-consistent standard errors understate uncertainty severely, and two variance estimators are reported: the HC1 heteroskedasticity-consistent estimator, and Conley spatial heteroskedasticity and autocorrelation consistent (HAC) errors with a Bartlett kernel at 1 km, 2 km and 5 km cutoffs (Conley 1999). Kernel distances are computed in a local equirectangular projection tuned to the sample latitude, which reproduces WGS84 geodesic distance across the county with a root mean square error of 90 m; the equal-area EPSG:5070 grid that defines the analysis cells distorts distance five times as much and is not used for the kernel. Spatial block clustering was also examined and is not tabulated, because the block standard error depends on where the arbitrary grid origin falls. Across 25 origin offsets at a 2 km block size, the headline standard error ranges from 1.64 to 2.19, a 30 percent spread, which moves t between minus 10.0 and minus 13.4. Conley requires no such choice and its estimate converges, changing by less than 0.1 percent between 5 km and 8 km cutoffs, so the 5 km figure is reported as the conservative bound rather than as an arbitrary stopping point.'));

// --- Equation 4: the estimating equation
body.push(eq([
  { t: 'y', i: true }, { t: 'i', i: true, sub: true },
  { t: ' = ' }, { t: '\u03b2', i: true }, { t: '0', sub: true },
  { t: ' + ' }, { t: '\u03b2', i: true }, { t: '1', sub: true },
  { t: ' ' }, { t: 'C', i: true }, { t: 'i', i: true, sub: true },
  { t: ' + ' }, { t: 'x', i: true }, { t: 'i', i: true, sub: true },
  { t: '\u2032' }, { t: '\u03b3', i: true }, { t: ' + ' }, { t: '\u03b5', i: true }, { t: 'i', i: true, sub: true }
], 4));
body.push(where([
  { t: 'where ' }, { t: 'y', i: true }, { t: 'i', i: true, sub: true },
  { t: ' is one of the three outcomes, ' }, { t: 'C', i: true }, { t: 'i', i: true, sub: true },
  { t: ' is canopy cover above 2 m on the unit interval, and ' },
  { t: 'x', i: true }, { t: 'i', i: true, sub: true },
  { t: ' collects the four covariates with ' }, { t: 'γ', i: true },
  { t: ' the corresponding coefficient vector, ' }, { t: 'β', i: true }, { t: '0', sub: true },
  { t: ' the intercept and ' }, { t: 'ε', i: true }, { t: 'i', i: true, sub: true },
  { t: ' the error term. Because ' }, { t: 'C', i: true }, { t: 'i', i: true, sub: true },
  { t: ' runs from 0 to 1, ' }, { t: '\u03b2', i: true }, { t: '1', sub: true },
  { t: ' is the change across the full canopy range rather than a per-unit slope, which is how every '
       + 'coefficient in this paper should be read. Two readings follow. Across the interquartile range of observed canopy, 0.19 to 0.68, the same coefficient implies 10.6 points of measured impervious surface and a 15 point change in detection failure, which is the comparison between typical parcels. The full-range figure is not an extrapolation: 1.2 percent of the sample sits at complete canopy and 11.1 percent at 0.05 or below, so both ends of the contrast are populated by parcels that carry a recorded dwelling. Equation 4 is ordinary least squares; because two of '
       + 'the three outcomes are binary it is a linear probability model, reported because the coefficient '
       + 'is then directly interpretable as a change in probability. Fitted values fall outside the unit '
       + 'interval for 0.07 percent of observations on the detection-failure outcome and 5.0 percent on '
       + 'the assumption-free one, so the coefficients are average partial effects and not probabilities '
       + 'for any individual cell. A logit fitted to the same specifications gives average marginal '
       + 'effects of plus 0.305 and plus 0.166 against the linear plus 0.312 and plus 0.160, so nothing '
       + 'in the paper turns on the functional form. Standard errors follow Conley (1999).' }
]));


// ============================== 3. RESULTS ==============================
body.push(h1('3. Results'));

body.push(h2('3.1. The bound behaves as a bound'));
body.push(p('Figure 3 shows what the bound is testing, using two parcels matched on everything the analysis controls for. Both dwellings were built in 1998, both sit on 0.29 acres, and their recorded floor areas differ by 51 square feet, so their physical bounds are 20.5 and 22.7 percent. One is open ground and one is under closed canopy. NLCD reports 38 percent impervious at the first and 1 percent at the second, which is 21.7 points below the bound its recorded structure alone sets. Neither illustrated parcel is among the 35.2 percent whose roof is provably contained in its own cell (Section 2.2), so for this pair the bound is the aggregate one; the pair was selected for typicality, and the straddle-free subset is reported separately in Section 3.6.'));

body.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 160, after: 80 },
  keepNext: true,
  children: [new ImageRun({
    type: 'png',
    altText: { name: 'Figure 3. Canopy and measured impervious surface at two matched parcels', title: 'Figure 3. Canopy and measured impervious surface at two matched parcels', description: 'Six panels comparing two matched residential parcels, one on open ground and one under closed canopy, each covering the same 180 m extent. The top row shows aerial imagery, the middle row canopy height in metres, and the bottom row NLCD percentage developed impervious at 30 m with the analysed cell outlined. Rooftops are visible through canopy gaps at the canopied parcel, yet the product reports 1 percent impervious there against 38 percent at the open parcel.' },
    data: fs.readFileSync(path.join(HERE, 'figure_matched_parcels.png')),
    transformation: figFit(path.join(HERE, 'figure_matched_parcels.png'), 624)
  })]
}));
body.push(caption('Figure 3. Canopy and measured impervious surface at two matched parcels. Both are residential parcels in Nevada County, California. (a, d) National Agriculture Imagery Program (NAIP) aerial imagery at 0.6 m, acquired 24 July 2020, the acquisition nearest the NLCD 2019 epoch; both dwellings date from 1998 and so predate all imagery shown. (b, e) Meta and WRI canopy height in metres; the inset label gives the cover fraction above 2 m, which is the treatment variable used in the analysis, not the height shown by the colour scale. (c, f) NLCD 2019 percentage developed impervious, rendered at native 30 m resolution; the red square is the NLCD cell containing the parcel centroid, positioned on the EPSG:5070 grid. All six panels cover the same 180 m extent and are north-up. Rooftops are visible through canopy gaps in (d), so the structures are present and the assessor records them, yet the product reports 1 percent impervious. The pair was drawn from 3,530 candidate matches and selected for typicality rather than contrast: its NLCD values, 38 and 1 percent, are exactly the medians of the low-canopy and high-canopy groups in the analysis sample. NLCD values were re-extracted independently in Google Earth Engine at these coordinates and agree with the analysis dataset.'));
body.push(p('The companion land-cover product makes the same error categorically. Only 83.0 percent of assessed dwellings sit in a cell NLCD assigns to a developed class: 14.0 percent sit in cells classed evergreen forest and 17.0 percent in something other than developed, rising from 13.4 percent in the lowest canopy decile to 34.5 percent in the highest. Turning to the impervious layer, 58.8 percent of recorded dwellings sit in a cell whose measured impervious percentage falls below the roof-only bound. Figure 4 shows the two series by canopy decile. The bound falls with canopy, by 42 percent across the range, which is real: high-canopy cells genuinely hold less recorded roof. Measured impervious falls by 80 percent over the same range. The series cross at the fourth decile and diverge from there, and that divergence is the object of study. The level at the open end is not itself evidence of occlusion. Already 43.7 percent of parcels in the lowest canopy decile sit in a cell reporting less than the bound. Three things contribute: centroid assignment (Section 2.2), under which a whole roof is counted against a cell that may hold only part of it; attached garages, which on their own lift the breach rate from 49.8 to 58.8 percent; and the product’s documented insensitivity to low-density impervious surface. The canopy gradient is measured against that baseline, not from zero.'));

body.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 160, after: 80 },
  keepNext: true,
  children: [new ImageRun({ type: 'png',
    altText: { name: 'Figure 4. What the bound requires against what the product reports', title: 'Figure 4. What the bound requires against what the product reports', description: 'Two panels plotted against canopy cover by decile. The left panel plots the physical lower bound from recorded roof and the measured NLCD impervious percentage; the bound falls 42 percent across the canopy range while measured impervious falls 80 percent, the two series cross near 0.28 canopy, and they separate to 12.1 percentage points at the highest decile, with the gap shaded. The right panel plots detection failure: the share of parcels whose cell reports less than the bound rises from 43.7 to 81.6 percent, and the share whose cell reports exactly zero impervious surface rises from 12.5 to 36.3 percent. Error bars are 95 percent confidence intervals.' },
    data: fs.readFileSync(path.join(HERE, 'figure_divergence.png')),
    transformation: figFit(path.join(HERE, 'figure_divergence.png'), 624) })]
}));
body.push(caption('Figure 4. What the bound requires against what the product reports. Values are shown by canopy decile for the analysis sample (n = 21,931; 2,189 to 2,196 parcels per decile). (a) The physical bound falls 42 percent across the canopy range while measured impervious falls 80 percent. The series cross near 0.28 canopy and separate to 12.1 percentage points at the highest decile; the shaded region is impervious surface that recorded structures require and the product does not report. (b) The share of parcels whose cell reports less than the bound rises from 43.7 to 81.6 percent, and the share whose cell reports exactly zero impervious surface rises from 12.5 to 36.3 percent. Error bars are 95 percent confidence intervals on each decile mean, binomial in panel (b); they are smaller than the separation between the series throughout.'));

body.push(h2('3.2. Canopy, measured impervious surface and detection failure'));
body.push(p('Table 1 reports the three outcomes under the common specification. Regressing measured NLCD impervious percentage on canopy gives minus 21.90, so full canopy is associated with roughly 22 fewer percentage points of measured impervious surface than bare ground on otherwise comparable parcels. Under the most conservative spatial standard error, Conley at a 5 km cutoff, that is t equal to minus 9.7.'));

body.push(caption('Table 1. Canopy coefficient under the common specification. Analysis sample (n = 21,931). Covariates are parcel area, recorded floor area, terrain slope and neighbour count within 100 m. Canopy cover runs from 0 to 1, so each coefficient is the change across the full canopy range: percentage points for the first outcome, change in probability for the other two. Standard errors follow the coefficient; the 1 km, 2 km and 5 km columns are Conley spatial heteroskedasticity and autocorrelation consistent (HAC) errors with a Bartlett kernel at those cutoffs. The final column gives t at the 5 km cutoff, the most conservative of the three. Conley converges by 5 km, changing less than 0.1 percent at an 8 km cutoff.'));
body.push(makeTable([
  ['Outcome', 'Coefficient', 'R\u00b2', 'HC1', '1 km', '2 km', '5 km', 't (5 km)'],
  ['Measured impervious', '\u221221.8958', '0.320', '0.4262', '1.4381', '1.9006', '2.2613', '\u22129.7'],
  ['Below the physical bound', '+0.3119', '0.101', '0.0114', '0.0277', '0.0345', '0.0403', '+7.7'],
  ['Reports exactly zero', '+0.1598', '0.059', '0.0097', '0.0214', '0.0276', '0.0336', '+4.8']
], [26, 15, 9, 11, 11, 11, 11, 11]));

body.push(p('On the detection-failure outcome the canopy coefficient is plus 0.3119, with Conley t at 5 km of plus 7.7: the probability that the product reports less impervious surface than the recorded structures occupy is 31 percentage points higher at closed canopy than at bare ground. On the assumption-free outcome the coefficient is plus 0.1598 (Conley t at 5 km of plus 4.8), and the raw rate at which NLCD reports exactly zero impervious surface at an assessed dwelling rises from 12.5 percent in the lowest canopy decile to 36.3 percent in the highest. These are not three independent findings; they are one finding expressed on a continuous, a bounded and an assumption-free outcome, and they should be reported as such. They do differ in what they assume, however, and that distinction matters.'));

body.push(p('The first outcome is a regression of one optical product on another and the bound plays no part in it; a reader sceptical of the bound can still read minus 21.90, but it is not the paper’s contribution. The second and third are what the administrative reference buys, because only they ask whether the product reports less than a structure known from records to be present. The second depends on the bound being right; the third, which needs only that a dwelling is on the roll, does not.'));

body.push(h2('3.3. Canopy separates from settlement density'));
body.push(p('This is the test that distinguishes the result from published rural underestimation. If canopy operated only as a proxy for sparse settlement, the canopy gradient should vanish once density is held fixed. Table 2 shows it does not. The detection-failure rate rises with canopy in every density quartile, by 30, 28, 31 and 25 percentage points from the lowest to the highest canopy quintile. The rise is monotonic in the three more dispersed quartiles. In the densest it is not: the rate is essentially flat across the two lowest canopy quintiles, 35.5 and 33.1 percent, before climbing to 60.5. With at least 574 parcels in every group that dip is not a small-sample artefact, and it is reported rather than smoothed. The canopy effect in the densest stratum is real but its onset is delayed, which matches the curvature of this outcome across the whole frame: a quadratic in canopy puts the marginal effect on detection failure at plus 0.03 at no canopy and plus 0.64 under closed canopy, so the effect activates late. Density’s own coefficient, minus 0.0011 per neighbouring parcel, moves the outcome about one percentage point across the interquartile range of neighbour counts. Canopy moves it 31 points. Density is not doing this work.'));

body.push(caption('Table 2. Detection-failure rate by canopy quintile within settlement-density quartile. Values are the percentage of parcels whose cell falls below the physical bound, analysis sample (n = 21,931). Canopy quintiles are cut on the whole sample so columns are comparable across rows; group sizes range from 574 to 1,702 parcels.'));
body.push(makeTable([
  ['Density quartile', 'Mean neighbours, 100 m', 'Canopy Q1 (low)', 'Q2', 'Q3', 'Q4', 'Q5 (high)'],
  ['1 (dispersed)', '6.7', '54.9', '62.7', '69.1', '74.8', '84.5'],
  ['2', '12.5', '52.2', '55.4', '59.8', '63.0', '80.6'],
  ['3', '16.8', '43.6', '47.9', '55.2', '62.6', '74.8'],
  ['4 (densest)', '31.0', '35.5', '33.1', '40.2', '51.8', '60.5']
], [20, 16, 15, 11, 11, 11, 12]));

body.push(h2('3.4. Severity tracks the decision rule'));
body.push(p('The four products differ in how much evidence they require before recording built surface, and the loss of built signal across the canopy range orders accordingly (Table 3). A hard class assignment loses almost the entire signal, a continuous fraction loses roughly three quarters, and a class probability and a built-area estimate lose about half. The ordering is consistent with graded evidence degrading more gracefully under occlusion than evidence thresholded into a class. These data cannot establish that. The products also differ in resolution, at 10 m for WorldCover and Dynamic World, 30 m for NLCD and 100 m for GHSL, and in sensor, epoch and training data. Decision rule is confounded with all of them. What the data do establish is that four products disagree about the same parcels by amounts that scale with canopy. Subjecting each to the same test sharpens the choice: all four fall below the physical bound more often as canopy rises, but the rates differ by a factor of 3.5 and their ordering is not that of the level comparison. Only NLCD and WorldCover are measured in the same units as the bound, and between those two the rates differ by a factor of 1.3. Dynamic World and GHSL are reported for completeness. A class probability and a 100 m built-area density are not commensurable with a 900 m bound, so their levels should not be read as detection rates. WorldCover fails on 75.9 percent of parcels, Dynamic World on 21.6 percent.'));

body.push(caption('Table 3. Mean reported built-surface value by product and decision rule. Values are for the lowest and highest canopy quintiles, analysis sample (n = 21,931). Each product is reported in its own units and the levels are therefore not comparable across rows: WorldCover and GHSL are percentages of cell area assigned to the built class and to built surface respectively, NLCD is percentage impervious, and Dynamic World is a built-class probability on a 0 to 100 scale. Only the relative fall is comparable across products. The last two columns apply one test to all four, the percentage of parcels whose cell reports less built surface than the bound requires, and the canopy coefficient on that indicator, but the test inherits the unit problem above. It is a like-for-like comparison of area against area only for NLCD and WorldCover. For Dynamic World it sets a class probability against a percentage of cell area, and for GHSL a 100 m built-area density against a 900 m bound, so those two rows measure a definitional mismatch as well as any occlusion and their levels should not be read as detection rates. Standard errors in the final column are HC1, not the spatially robust errors of Table 1, and the t values are correspondingly optimistic. Quintiles hold between 4,384 and 4,390 parcels.'));
body.push(makeTable([
  ['Product', 'Decision rule', 'Low canopy', 'High canopy', 'Fall (%)', 'Below bound (%)', 'Canopy on below bound'],
  ['ESA WorldCover built-up', 'Hard class', '54.3', '0.9', '−98', '75.9', '+0.655 (t = 76.6)'],
  ['NLCD percentage impervious', 'Continuous fraction', '36.4', '10.0', '−72', '58.8', '+0.312 (t = 27.4)'],
  ['Dynamic World built', 'Class probability', '61.4', '31.2', '−49', '21.6', '+0.322 (t = 32.5)'],
  ['GHSL built surface', 'Built area', '20.6', '12.2', '−41', '72.2', '+0.096 (t = 8.7)']
], [23, 14, 10, 10, 8, 11, 19]));

body.push(h2('3.5. A documented production step as rival explanation'));
body.push(p('The Multi-Resolution Land Characteristics (MRLC) Consortium metadata for NLCD 2019 percentage impervious (MRLC 2021) records that DMSP and VIIRS nighttime lights were \u201csuperimposed on NLCD 2011 Impervious Surface data to exclude low density impervious areas outside urban and suburban centers\u201d. That is a documented production step that removes impervious surface in precisely the setting studied here, and it correlates with canopy: canopy and VIIRS radiance correlate at minus 0.298, and mean radiance falls from 5.48 in the lowest canopy decile to 1.19 in the highest. The two layers are separable and are reported separately. Adding VIIRS radiance alone moves the canopy coefficient from minus 21.90 to minus 18.71; adding both nighttime layers gives minus 18.49; adding elevation as well gives minus 18.13, with Conley t at 5 km improving to minus 13.2 because standard errors shrink faster than the coefficient. Elevation alone moves it only to minus 20.60, so the attenuation is carried by radiance rather than by terrain, which matters because elevation predicts conifer cover in a foothill county. The nighttime-lights step accounts for roughly one sixth of the effect and leaves the remainder.'));

body.push(p('Whether this constitutes control or over-control is unresolved and the paper does not resolve it. Dense canopy suppresses upward light emission as well as reflected daylight, so radiance may mediate the canopy effect rather than confound it. Treating it as a confounder gives minus 18.13, as a mediator minus 21.90, and the result is therefore reported as a range of 18 to 22 points rather than a point estimate. Naming the production step is in any case a sharper contribution than attributing the error to the sensor alone.'));

body.push(h2('3.6. Method validation'));
body.push(p('Six checks test whether the method measures what it claims, and a further ladder of frame restrictions tests whether any subgroup produces it (Table 4). None is a proof of construct validity; each removes a specific alternative explanation. First, the result is not a reflection of genuinely sparser building. Canopy does predict a lower physical bound, at minus 7.58, so measured impervious could in principle be tracking something real; but adding the bound itself to the specification leaves the canopy coefficient at minus 21.15, essentially unchanged. Conditioning on the recorded roof does not absorb the gradient.'));

body.push(p('Second, the parcel-centroid assignment rule does not generate the result. Assignment error is not independent of canopy, since parcel area correlates with canopy at plus 0.283, so this was tested rather than assumed. The detection-failure coefficient is flat across parcel-area quartiles, at plus 0.3393, plus 0.3163, plus 0.3458 and plus 0.3158, spanning 9 percent of its own magnitude over a 2.4-fold range of parcel area. Differential assignment error would have to be almost exactly scale-invariant to produce a constant coefficient across that range, which is possible but is a much more specific claim than the one it would be used to support.'));

body.push(p('Third, parcels built after the product epoch behave as a negative control should: minus 2.45 against minus 21.90, with a 95 percent interval of minus 6.0 to plus 1.0. Being small, it excludes an effect larger than about a quarter of the headline rather than excluding one altogether, and it does carry treatment variation, canopy averaging 0.396 against 0.444. Two caveats: on the assumption-free outcome it returns minus 0.219, t of minus 3.5 on 589 parcels, a sign reversal rather than a null, and the below-floor outcome sits near its ceiling there. Read the continuous outcome. Fourth, the estimate depends on the covariate set in a bounded way: canopy alone gives minus 31.44, the reported specification minus 21.90, every covariate minus 21.27, with parcel area accounting for 72 percent of that movement. Sign, significance and order of magnitude hold, as does the canopy threshold, minus 21.90 at 2 m against minus 22.67 at 5 m.'));
body.push(p('Fifth, the reference itself was validated independently. Microsoft Building Footprints, from Bing imagery by another vendor and algorithm, carries 81,849 buildings in the county in the release used here, captured in 2018 and 2019 at dates that do not differ by canopy. Footprint area was summed per 30 m cell across 700 cells, 70 per canopy decile, and read on the 569 single-parcel cells, where the two quantities describe one structure. In the two lowest deciles the median ratio of detected footprint to recorded roof is 1.01, the product exceeds the record in 50.5 percent of cells and finds nothing in 2.7 percent: where occlusion is absent it matches the record and is as often above as below, so the record is not inflated. In the two highest deciles the median falls to 0.54, exceedance to 24.8 percent, and 30.6 percent of cells hold no detected building, Mann-Whitney p below 1e-7. The recorded roof is canopy-blind, so that decline belongs to the imagery: a second optical product reproduces the gradient.'));
body.push(p('Sixth, the same assignment rule is tested where it does not bind at all. On the 7,721 parcels whose roof is provably contained in its own cell, where the bound is exact rather than aggregate, the continuous coefficient is minus 22.94, Conley t at 5 km of minus 10.3, against minus 21.90; the detection-failure coefficient is plus 0.309, t of plus 7.1, indistinguishable from plus 0.312. The breach rate falls from 58.8 to 53.1 percent and its lowest-decile value from 43.7 to 39.1, the direction expected if straddling roofs inflate the bound. Exact cells remove a known inflation in the level without weakening the gradient.'));
body.push(p('Finally, no part of the frame carries the result alone. Four restrictions were applied in turn: to cells where truncation does not bind, to single-parcel cells, to the dominant use code, and to lots of at least 0.05 acres. Across all four the continuous coefficient moves only between minus 19.65 and minus 21.90, t between minus 9.0 and minus 11.1. Each raises the detection-failure coefficient, from plus 0.312 to between plus 0.327 and plus 0.350. The restrictions that drop the least typical parcels strengthen the finding.'));

body.push(caption('Table 4. Validation checks and sensitivity. Analysis sample (n = 21,931) except where noted. Coefficients are on canopy cover above 2 m, which runs from 0 to 1, so they express the change across the full canopy range. The outcome is measured NLCD impervious percentage, in percentage points, except in the four rows reporting coefficients to three or four decimal places, where it is the binary detection-failure indicator and the coefficients are changes in probability, and in the second row, where it is the physical bound itself. The negative control is the 589 parcels built after the product epoch. Standard errors are HC1 through the garage-excluded bound, and Conley spatial heteroskedasticity and autocorrelation consistent errors at a 5 km cutoff from the porch-inclusive bound onward, which is the conservative choice and matches the inference reported for the headline outcomes in Table 1.'));
body.push(makeTable([
  ['Check', 'Result', 'Interpretation'],
  ['Conditioning on the physical bound', '−21.15 (t = −49.5)', 'Gradient is not real roof variation'],
  ['Canopy on the bound itself', '−7.58 (t = −23.7)', 'Bound does fall with canopy, but does not explain the gradient'],
  ['Detection failure by parcel-area quartile', '+0.339, +0.316, +0.346, +0.316', 'Scale invariant; assignment error excluded'],
  ['Negative control, built after 2019', '−2.45 (t = −1.4)', 'No effect where none should exist'],
  ['Covariate set, minimal to maximal', '−31.44 to −21.27', 'Not a specification artefact'],
  ['Canopy threshold, 2 m against 5 m', '−21.90 against −22.67', 'Robust to threshold choice'],
  ['Quadratic in canopy', '+9.07 (t = 6.1)', 'Convex under HC1, not separable from zero under spatial HAC'],
  ['Bound excluding attached garages', '+0.3236 (t = 27.7)', 'Including garages raises the bar and lowers the estimate'],
  ['Bound including recorded porch area', '+0.269 (t = 7.5)', 'Counting all recorded roof raises the breach rate to 68.2 percent'],
  ['Quadratic in canopy, detection failure', '+0.3063 (t = 4.3)', 'Marginal effect +0.03 at no canopy, +0.64 under closed canopy'],
  ['Dropping cells where truncation binds', '−21.83 (t = −9.7)', 'The 33 oversized-structure cells do not drive the result'],
  ['Cells holding one parcel only', '−19.65 (t = −9.0)', 'Not produced by summing footprints across parcels'],
  ['Dominant use code only', '−19.67 (t = −11.1)', 'Not produced by the 13.2 percent outside it'],
  ['Lots of at least 0.05 acres', '−20.98 (t = −10.0)', 'Not produced by condominium-style parcels'],
  ['Roof provably inside its own cell', '−22.94 (t = −10.3)', 'Gradient holds where the bound is exact']
], [29, 23, 48], { alignCols: [AlignmentType.LEFT, AlignmentType.CENTER, AlignmentType.LEFT] }));

body.push(h2('3.7. Consequence for a downstream user'));
body.push(p('The last comparison is against a published full-impervious reference, the impervious-surface coefficient of the California Office of Environmental Health Hazard Assessment (OEHHA 2010). It is applied here as a function of dwelling density, so it carries no image-derived information about these parcels, although its own calibration derives from photointerpretation elsewhere. Against it, NLCD sits 0.84 points above the reference in the lowest canopy decile, with half of parcels above it, and 25.87 points below in the highest, with 3 percent above. That is a swing of 26.7 points. It is computed on the 19,545 parcels whose dwelling density falls in the 1 to 50 dwelling units per acre range over which the coefficient is applied here; the remaining 2,386 lie outside it. The calibration at low canopy is the check that matters, and it passes.'));

body.push(p('The regulatory comparison is starker than any runoff figure. Where impervious cover is used as a total maximum daily load (TMDL) surrogate, the thresholds are narrow and low. Connecticut sets aquatic-life impairment at 12 percent impervious cover and the waste-load and load-allocation target at 11 percent. The intervening single percentage point is the explicit margin of safety (Connecticut DEP 2006). The observed shortfall at dwelling cells in the highest canopy decile is 12.1 points, and the canopy-associated difference across the full range is 18 to 22 points; either exceeds the single percentage point separating Connecticut’s threshold from its target. That comparison is at the cell, not the catchment. A catchment mean mixes dwelling cells with cells holding no structure, where bound and product agree at zero, so the catchment-scale error is smaller by a factor that depends on settlement share and is not estimated here. The claim is that the error is large where the structures are, not that a named catchment is misclassified.'));

body.push(p('Through the Technical Release 55 (TR-55) curve-number method of the US Soil Conservation Service (USDA SCS 1986), at a 3-inch 24-hour storm on hydrologic soil group B, runoff computed from NLCD is 76 percent of runoff computed from the bound, and 60 percent in the highest canopy decile. Both figures are ratios against a floor rather than against a measured truth, so they bracket rather than estimate the shortfall, and the bracket is one-sided only where the straddle correction of Section 2.2 does not bite. The calculation is illustrative and not a water budget: TR-55 is applied here well below its intended catchment scale, and the curve number is not linear in impervious fraction.'));

// ============================== 4. DISCUSSION ==============================
body.push(h1('4. Discussion'));

body.push(h2('4.1. What is claimed'));
body.push(p('A word on what is claimed. The error documented here is a bias in the measurement sense: systematic rather than random, and predictable from canopy cover. It is not a demonstration that canopy causes it. Three mechanisms fit what is observed: occlusion, spectral mixing of the built signal by any vegetation, and the documented nighttime-lights production step. Only the third is partly quantified, at roughly one sixth of the effect (Section 3.5). These data cannot separate the first two, which is why the language throughout is associational.'));
body.push(h2('4.2. Transferability of the reference'));
body.push(p('The methodological point is separable from the empirical one. Validating a remotely sensed product against a reference that shares its sensing modality cannot detect error mechanisms acting on both. Administrative property records break that dependence, and where they carry floor area and storey count they support not merely an alternative areal estimate but a physical bound: a testable claim about named cells, exact where the recorded roof falls wholly inside the cell and aggregate elsewhere.'));
body.push(p('The method needs two assessor fields, and their reach is estimated from published coverage rather than demonstrated, which is the weakest part of the transferability claim. The Historical Settlement Data Compilation for the United States (HISDAC-US) was assembled from assessor records covering roughly 200 million parcels in more than 3,100 counties, and its built-up intensity layer uses assessor-reported gross indoor floor area, the quantity used here (Leyk and Uhl 2018; Ahn et al. 2024). Living area is missing for 28.6 percent of residential records there, so roughly seven in ten carry it (Nolte et al. 2024). Both fields are required by rule in New York and New Jersey and by the Massachusetts parcel standard, and both appear in the Massachusetts, Utah and New Jersey statewide layers. Storey count is the weaker: no national completeness figure is published, and Florida, Wisconsin, North Carolina and Minnesota drop it while republishing floor area. Assuming a flat storey count in its place is not a safe substitute, and the cost is measurable here: recorded storeys rise from 1.42 to 1.61 across canopy deciles, so a flat assumption overstates roofs exactly where canopy is densest and inflates the detection-failure coefficient from plus 0.312 to plus 0.382, a bias of 22 percent in the direction of the hypothesis. That is the best case for a flat assumption, because the value used is the analysed sample\u2019s own mean storey count, which a replicator lacking the field would not know.'));

body.push(p('Floor area is itself defined inconsistently, so an implementation must state which variant it consumes. Neither obstacle is fundamental; both sit in the county mass-appraisal systems the state layers derive from. The approach also generalises to any occlusion mechanism, including terrain shadow and seasonal cover.'));

body.push(h2('4.3. Limitations'));
body.push(p('The limitations are real and several of them bound the claim rather than threaten it. The frame is parcels under half an acre carrying a recorded dwelling, which is what makes a recorded roof informative about a 30 m cell. Within that frame the continuous coefficient declines with parcel area, from minus 34.06 in the smallest quartile to minus 13.93 in the largest. The magnitude should therefore not be read as county-wide. The detection-failure coefficient is flat across the same quartiles, so the existence of the effect generalises within the frame even though its magnitude does not. Claims belong to small-lot residential settlement, which is where these products are used for stormwater and equity purposes in any case.'));

body.push(p('Four further limitations deserve statement. Parcels are assigned by centroid rather than polygon, which is quantified in Section 2.2 and tested in Section 3.6 rather than left as noise. Canopy is itself an optical product, so measurement error in the treatment attenuates the estimate towards zero, working against the finding. The bound assumes recorded structures exist as recorded, so unrecorded demolitions would produce spurious breaches. Finally, the relationship is not linear. A quadratic term is plus 0.306 on detection failure, Conley t of plus 4.3, and plus 9.07 on measured impervious surface, where it is significant under HC1 but not under spatial HAC. The reported coefficients are average slopes.'));

body.push(h2('4.4. External validity and the urban extension'));
body.push(p('One distributional result is worth reporting because it tells the urban extension where to look, and worth hedging because this county cannot carry it. The canopy penalty is larger on lower-valued parcels, running from minus 24.40 in the lowest improvement-value quintile to minus 17.30 in the highest, with a negative canopy-by-value interaction (minus 0.078 on the detection-failure outcome, t equal to minus 5.4, year built controlled). An error worse on cheaper homes is regressive in the direction the equity literature predicts. Two things stop it being an equity finding: California assessed value under Proposition 13 reflects purchase date as much as market value, and the pattern reverses among homes built between 1985 and 2000. Canopy here tracks terrain rather than wealth, correlating with improvement value at minus 0.054, and the county is 89.7 percent White alone and 0.8 percent Black (US Census Bureau 2025), so a race-stratified test would rest on roughly 175 parcels. The distributional question needs urban counties where canopy is socially patterned (Schwarz et al. 2015; Locke et al. 2021).'));

body.push(p('The most important limitation is external: this is one county, and a conifer-dominated one: within the frame the NLCD forest classes hold 3,075 evergreen against 50 deciduous and 67 mixed parcels. That composition rules out the mechanism test that would most sharply discriminate occlusion from spectral mixing, since deciduous canopy is transparent to leaf-off imagery and evergreen is not. Replication should therefore be chosen for forest composition rather than adjacency, and a mixed-forest county would permit the leaf-off contrast directly. Adjacency was not the binding constraint in any case. Placer County, adjacent and holding by far the larger stock of small residential parcels, publishes no storey count, so the bound cannot be constructed there at all, and the sensitivity above rules out substituting a flat value for it. The single-county scope of the demonstration therefore follows from the data requirement of Section 4.2 rather than from convenience. Whether the effect persists in urban settings is an open and consequential question that these data cannot answer. It matters because urban canopy is patterned by income and race (Schwarz et al. 2015; Locke et al. 2021), and because the equity application of this product lives there (Culler et al. 2024). Three things differ in cities: occlusion geometry, an already high level of measured impervious surface, and published evidence pointing to overprediction rather than under-measurement.'));

// The sign-change reading is stated here deliberately as a hypothesis, and
// nowhere else in the paper. The project record (canopy_bias_results.md, 9a)
// directs: "Present it as a hypothesis the data motivate, never as a result."
// Nothing in this study tests it, so the paragraph says so in terms and names
// the reference a test would need. Do not promote any of it into Section 3, the
// abstract or the conclusions; make_tables.py asserts that it stays here.
body.push(p('One further reading deserves stating as a hypothesis rather than as a result. If the sign of the error turns with settlement density, so that the loss of measured built surface found here belongs to sparse settlement while dense areas offer an already saturated signal, then the national underestimation reported by Nowak and Greenfield (2010) and the metropolitan pattern reported by Wickham et al. (2020) are consistent rather than contradictory. Nothing measured here tests that. A test requires a reference that captures all impervious surface rather than roofs alone, either high-resolution imagery digitised in a validation subsample or a stormwater utility’s measured impervious area, and building one is the natural next step for this class of reference.'));

// ============================== 5. CONCLUSIONS ==============================
body.push(h1('5. Conclusions'));
body.push(p('A lower bound on impervious surface built from assessor floor area and storey count provides a validation reference whose construction uses no imagery. It therefore does not share the occlusion it is used to detect, although the product assessed and the canopy treatment both remain optical. It also turns disagreement into a testable claim about specific cells. Applied to 21,931 parcels and four products, it shows that tree canopy is associated with 18 to 22 fewer percentage points of measured NLCD impervious surface, and with a 31 point higher probability of reporting less built surface than the records require. The association persists within every settlement-density stratum of the frame, and survives conditioning on the bound itself. Loss of built signal also differs sharply across products, in a way consistent with how aggressively each thresholds evidence, though these data cannot establish that as the cause. A documented nighttime-lights production step accounts for roughly one sixth in the specifications reported here, with radiance rather than terrain carrying the attenuation. The method needs only a published parcel roll, and the scope of the demonstration is small-lot residential settlement in a single conifer county, which replication in mixed-forest and urban counties should now extend or refute.'));

// ============================== STATEMENTS ==============================
body.push(h1('Acknowledgements'));
body.push(p('Nevada County, California, publishes the assessor parcel records that make this method possible, and the approach depends on that record being open. This work was conducted as part of the author\u2019s doctoral research in the Department of Civil and Environmental Engineering, Stanford Doerr School of Sustainability, within the Natural Capital Alliance, the Lepech Research Group, and the Center for Integrated Facility Engineering. The author thanks Kristy Hsiao for generous individual support of this research.'));

body.push(h1('Funding'));
body.push(p('This work was supported by the National Science Foundation Graduate Research Fellowship Program under grant DGE-2146755, the National GEM Consortium, the Cyrus Tang Foundation, John Miller, the Stanford Woods Institute for the Environment, and The Heinz Foundations. The funders had no role in the design of the study, in the collection, analysis and interpretation of data, or in the decision to submit this work for publication.'));

body.push(h1('Disclosure statement'));
body.push(p('The author reports there are no competing interests to declare.'));

body.push(h1('Ethics statement'));
body.push(p('This study used publicly available administrative and remotely sensed data only. Nevada County assessor parcel data are public under California law, and the satellite and aerial products are openly licensed. No human or animal participants were involved, so no ethics approval was required. Parcels are analysed in aggregate. The two parcels illustrated in Figure 3 are identified by assessor parcel number, which is a public identifier, and no occupant information was obtained or used at any stage.'));

body.push(h1('Declaration of generative AI use'));
body.push(p('A large language model (Anthropic Claude Opus 5) was used to write and debug the analysis, figure and verification code, to draft and revise prose, and to cross-check sources. The author specified the research question, the design and every analytical decision, verified all code, outputs and citations against primary sources, and is solely responsible for the data, analysis and conclusions. Generative AI was not used to generate or alter data or results, and is not credited as an author. The released reproduction package allows every reported value to be recomputed independently.'));

body.push(h1('Data availability statement'));
body.push(p('The parcel-level dataset supporting this study is released in full under a CC0 licence. It carries all 24,088 records of the frame with their derived variables, of which 21,931 form the analysis sample, 589 the post-epoch negative control and 1,568 are excluded for want of a recorded year built. Released with it are the recorded secondary attributes used in the robustness checks, the exact centroid-to-cell-edge distances underpinning the straddle correction, the building-footprint validation sample of 700 cells, the Google Earth Engine extraction code, the Python that draws the figures, the analysis code including the Conley spatial variance estimator and the verification harness, and the runoff calculation. The dataset and code are deposited at https://doi.org/10.5281/zenodo.23072749. Source data are public: Nevada County assessor parcel records, NLCD 2019, ESA WorldCover, Dynamic World, GHSL, and the Meta and WRI canopy-height model.'));

body.push(h1('Author contributions'));
body.push(p('Devan Cantrell Addison-Turner is the sole author. Contributor Roles Taxonomy (CRediT) statement, Devan Cantrell Addison-Turner: Conceptualization, Data curation, Formal analysis, Investigation, Methodology, Project administration, Resources, Software, Validation, Visualization, Writing \u2013 original draft, and Writing \u2013 review and editing. He approved the version to be published and agrees to be accountable for all aspects of the work.'));

// ============================== REFERENCES ==============================
body.push(h1('References'));

const refs = [
  'Ahn, Y., S. Leyk, J.H. Uhl, and C.M. McShane. 2024. \u201cAn integrated multi-source dataset for measuring settlement evolution in the United States from 1810 to 2020.\u201d Scientific Data 11 (1): 275. doi:10.1038/s41597-024-03081-x.',
  'Brown, C.F., S.P. Brumby, B. Guzder-Williams, T. Birch, S.B. Hyde, J. Mazzariello, W. Czerwinski, et al. 2022. \u201cDynamic World, near real-time global 10 m land use land cover mapping.\u201d Scientific Data 9: 251. doi:10.1038/s41597-022-01307-4.',
  'Conley, T.G. 1999. \u201cGMM estimation with cross sectional dependence.\u201d Journal of Econometrics 92 (1): 1\u201345. doi:10.1016/S0304-4076(98)00084-0.',
  'Connecticut DEP (Connecticut Department of Environmental Protection). 2006. \u201cPercent impervious cover as a surrogate target for TMDL analyses in Connecticut.\u201d Appendix 2, Connecticut Watershed Response Plan for Impervious Cover, last revised 14 December 2006. Hartford, CT. https://portal.ct.gov/-/media/deep/water/ic/watershed_response_plan_for_ic/appendix2percenticassurrogatetargetpdf.pdf.',
  'Culler, M., J. Wickham, M.S. Nash, and M.T. Clement. 2024. \u201cImpervious cover change as an indicator of environmental equity.\u201d Remote Sensing Applications: Society and Environment 35: 101247. doi:10.1016/j.rsase.2024.101247.',
  'Dewitz, J. 2021. National Land Cover Database (NLCD) 2019 Products (ver. 3.0, February 2024). U.S. Geological Survey data release. doi:10.5066/P9KZCM54.',
  'Leyk, S., and J.H. Uhl. 2018. \u201cHISDAC-US, historical settlement data compilation for the conterminous United States over 200 years.\u201d Scientific Data 5: 180175. doi:10.1038/sdata.2018.175.',
  'Locke, D.H., B. Hall, J.M. Grove, S.T.A. Pickett, L.A. Ogden, C. Aoki, C.G. Boone, and J.P.M. O\u2019Neil-Dunne. 2021. \u201cResidential housing segregation and urban tree canopy in 37 US cities.\u201d npj Urban Sustainability 1: 15. doi:10.1038/s42949-021-00022-0.',
  'MRLC (Multi-Resolution Land Characteristics Consortium). 2021. NLCD 2019 Percent Developed Imperviousness (CONUS): Product Metadata. Sioux Falls, SD: US Geological Survey. https://www.mrlc.gov/downloads/sciweb1/shared/mrlc/metadata/nlcd_2019_impervious_l48_20210604.xml.',
  'Nolte, C., K.J. Boyle, A.M. Chaudhry, C. Clapp, D. Guignet, H. Hennighausen, I. Kushner, et al. 2024. \u201cData practices for studying the impacts of environmental amenities and hazards with nationwide property data.\u201d Land Economics 100 (1): 200\u2013221. doi:10.3368/le.100.1.102122-0090r.',
  'Nowak, D.J., and E.J. Greenfield. 2010. \u201cEvaluating the National Land Cover Database tree canopy and impervious cover estimates across the conterminous United States: a comparison with photo-interpreted estimates.\u201d Environmental Management 46 (3): 378\u2013390. doi:10.1007/s00267-010-9536-9.',
  'OEHHA (Office of Environmental Health Hazard Assessment). 2010. User\u2019s Guide for the California Impervious Surface Coefficients. Sacramento, CA: Ecotoxicology Program, California Environmental Protection Agency. https://oehha.ca.gov/media/downloads/ecotoxicology/document/iscusersguide.pdf.',
  'Pesaresi, M., M. Schiavina, P. Politis, S. Freire, K. Krasnod\u0119bska, J.H. Uhl, A. Carioli, et al. 2024. \u201cAdvances on the Global Human Settlement Layer by joint assessment of Earth Observation and population survey data.\u201d International Journal of Digital Earth 17 (1): 2390454. doi:10.1080/17538947.2024.2390454.',
  'Pilant, A., K. Endres, D. Rosenbaum, and G. Gundersen. 2020. \u201cUS EPA EnviroAtlas meter-scale urban land cover (MULC): 1-m pixel land cover class definitions and guidance.\u201d Remote Sensing 12 (12): 1909. doi:10.3390/rs12121909.',
  'Schwarz, K., M. Fragkias, C.G. Boone, W. Zhou, M. McHale, J.M. Grove, J. O\u2019Neil-Dunne, et al. 2015. \u201cTrees grow on money: urban tree canopy cover and environmental justice.\u201d PLOS ONE 10 (4): e0122051. doi:10.1371/journal.pone.0122051.',
  'Tolan, J., H.-I. Yang, B. Nosarzewski, G. Couairon, H.V. Vo, J. Brandt, J. Spore, et al. 2024. \u201cVery high resolution canopy height maps from RGB imagery using self-supervised vision transformer and convolutional decoder trained on aerial lidar.\u201d Remote Sensing of Environment 300: 113888. doi:10.1016/j.rse.2023.113888.',
  'Uhl, J.H., H. Zoraghein, S. Leyk, D. Balk, C. Corbane, V. Syrris, and A.J. Florczyk. 2020. \u201cExposing the urban continuum: implications and cross-comparison from an interdisciplinary perspective.\u201d International Journal of Digital Earth 13 (1): 22\u201344. doi:10.1080/17538947.2018.1550120.',
  'Uhl, J.H., S. Leyk, C.M. McShane, A.E. Braswell, D.S. Connor, and D. Balk. 2021. \u201cFine-grained, spatiotemporal datasets measuring 200 years of land development in the United States.\u201d Earth System Science Data 13: 119\u2013153. doi:10.5194/essd-13-119-2021.',
  'US Census Bureau. 2025. QuickFacts: Nevada County, California. Vintage V2025 estimates. Washington, DC: US Department of Commerce. https://www.census.gov/quickfacts/fact/table/nevadacountycalifornia.',
  'US EPA (US Environmental Protection Agency). 2015. Innovative TMDLs Using Impervious Cover. Washington, DC: Office of Water. https://www.epa.gov/tmdl/innovative-tmdls-using-impervious-cover.',
  'USDA SCS (United States Department of Agriculture, Soil Conservation Service). 1986. Urban Hydrology for Small Watersheds. Technical Release 55, 2nd ed. Washington, DC: USDA.',
  'Wickham, J., S.V. Stehman, A.C. Neale, and M. Mehaffey. 2020. \u201cAccuracy assessment of NLCD 2011 percent impervious cover for selected USA metropolitan areas.\u201d International Journal of Applied Earth Observation and Geoinformation 84: 101955. doi:10.1016/j.jag.2019.101955.',
  'Wickham, J., S.V. Stehman, D.G. Sorenson, L. Gass, and J.A. Dewitz. 2021. \u201cThematic accuracy assessment of the NLCD 2016 land cover for the conterminous United States.\u201d Remote Sensing of Environment 257: 112357. doi:10.1016/j.rse.2021.112357.',
  'Wickham, J., S.V. Stehman, D.G. Sorenson, L. Gass, and J.A. Dewitz. 2023. \u201cThematic accuracy assessment of the NLCD 2019 land cover for the conterminous United States.\u201d GIScience & Remote Sensing 60 (1): 2181143. doi:10.1080/15481603.2023.2181143.',
  'Wickham, J., S.V. Stehman, D.G. Sorenson, L. Gass, J.A. Dewitz, and J.V. Kilaru. 2026. \u201cThematic accuracy assessment of the National Land Cover Database (NLCD2021) for the conterminous United States.\u201d GIScience & Remote Sensing 63 (1): 2659490. doi:10.1080/15481603.2026.2659490.',
  'Yang, L., S. Jin, P. Danielson, C. Homer, L. Gass, S.M. Bender, A. Case, et al. 2018. \u201cA new generation of the United States National Land Cover Database: requirements, research priorities, design, and implementation strategies.\u201d ISPRS Journal of Photogrammetry and Remote Sensing 146: 108\u2013123. doi:10.1016/j.isprsjprs.2018.09.006.',
  'Zanaga, D., R. Van De Kerchove, D. Daems, W. De Keersmaecker, C. Brockmann, G. Kirches, J. Wevers, et al. 2022. ESA WorldCover 10 m 2021 v200 [Dataset]. Zenodo. doi:10.5281/zenodo.7254221.',
];
refs.forEach(r => body.push(new Paragraph({
  alignment: AlignmentType.LEFT,
  spacing: { line: LINE, after: 60 },
  indent: { left: 360, hanging: 360 },
  children: [new TextRun({ text: r, font: FONT, size: SZ_SM })]
})));

const doc = new Document({
  creator: 'Devan Cantrell Addison-Turner',
  lastModifiedBy: 'Devan Cantrell Addison-Turner',
  // The document title must be the manuscript's full title. It was truncated
  // at "built-surface products", dropping the second half.
  title: 'An optically independent administrative reference for validating built-surface products, and the tree-canopy bias it reveals',
  description: 'Measurement paper submitted to GIScience & Remote Sensing.',
  keywords: 'impervious surface; accuracy assessment; tree canopy; cadastral and assessor data; NLCD; validation reference',
  styles: { default: { document: { run: { font: FONT, size: SZ } } } },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 200, after: 0 },
          children: [new TextRun({
            children: [PageNumber.CURRENT],
            font: FONT,
            size: SZ_SM
          })]
        })]
      })
    },
    children: body
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(path.join(HERE, 'canopy_bias_manuscript_GIScienceRS.docx'), buf);
  console.log('written', buf.length, 'bytes');
});
