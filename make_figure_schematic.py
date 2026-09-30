#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Devan Cantrell Addison-Turner, ORCID 0000-0002-2511-3680
# Department of Civil and Environmental Engineering, Stanford University
#
# From the reproduction package for "An optically independent administrative
# reference for validating built-surface products, and the tree-canopy bias it
# reveals", a manuscript prepared for GIScience & Remote Sensing. Not yet
# published; cite the repository until it is. Citation metadata: CITATION.cff.
#
# https://github.com/devanaddisonturner/Canopy-Bias-Nevada
# Code MIT, released data CC0 1.0.
# ---------------------------------------------------------------------------
"""
Method schematic. How an optically independent lower bound on impervious
surface is built from an assessor record, and what it is compared against.

Uses the canopied parcel of Figure 3, APN 045-300-033, so the
numbers on this diagram are the same ones that appear there and in the data.
Laid out as a single left-to-right row, so the four steps read as one flow;
panel height is set by HEIGHT_IN below and the output stays at 300 dpi.

    python3 make_figure_schematic.py [nevada_canopy_bias_rowlevel.csv]

Writes PNG and LZW TIFF at 300 dpi.
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'nevada_canopy_bias_rowlevel.csv')
APN = '045300033000'

SERIF = 'Liberation Serif'
plt.rcParams.update({'font.family': 'serif', 'font.serif': [SERIF, 'DejaVu Serif']})

d = pd.read_csv(CSV, dtype={'apn': str, 'px': str})
r = d[d.apn == APN].iloc[0]
sqft, storeys = float(r.sqft), int(r.storeys)
garage_sqft = float(r.garage)
dwell_m2 = (sqft / storeys) * 0.092903
garage_m2 = garage_sqft * 0.092903
roof_m2 = dwell_m2 + garage_m2               # reproduces the roof_m2 column exactly
assert abs(roof_m2 - float(r.roof_m2)) < 0.01, 'footprint identity broken'
bound = float(r.imp_floor_px)
nlcd = float(r.nlcd)
n_bldg = int(r.n_bldg_px)
CELL_M2 = 900.0

INK = '#1f2933'
# Series palette, chosen by measurement rather than by eye. The earlier pair
# (#1f4e79 / #b8560f) was safe but not best: simulated protanopia, deuteranopia
# and tritanopia gave a worst-case separation of 110, and the product colour
# carried 4.80:1 against white. These two are the Okabe-Ito colour-blind-safe
# blue and vermillion, darkened so they also clear text contrast: worst-case
# separation 129, and 7.34:1 and 5.84:1 against white.
# The gap annotation was #a01b20, which sat 39 from the product colour under
# tritanopia, below the separation threshold of 40. Deep maroon keeps the
# deficit-red reading and measures 72 from the product colour and 12.29:1
# against white. Across the whole co-occurring set the worst pair rises 39 -> 52.
BOUND_C = '#1A4A78'
NLCD_C = '#D06A10'
MISS_C = '#d62728'

# One row of four panels. WIDTH_IN is the text width of the page; HEIGHT_IN is
# the only knob that changes how tall the figure is, at unchanged 300 dpi.
WIDTH_IN, HEIGHT_IN = 7.2, 4.95
W, H = WIDTH_IN, HEIGHT_IN
fig = plt.figure(figsize=(W, H), dpi=300)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 100)
YMAX = 100 * H / W                           # equal units per inch on both axes
ax.set_ylim(0, YMAX)
ax.axis('off')

# four boxes across, with room between them for the connecting arrows
GAP = 7.2
BW = (100 - 2 * 1.6 - 3 * GAP) / 4.0
BH = YMAX - 13.0
X0 = 1.6
XS = [X0 + k * (BW + GAP) for k in range(4)]
BY = 2.2
TY = BY                                       # single row: every box shares a baseline
LX, RX = XS[0], XS[1]


def box(x, y, title):
    ax.add_patch(FancyBboxPatch((x, y), BW, BH, boxstyle='round,pad=0.7',
                                fc='white', ec='0.7', lw=0.9, zorder=1))
    ax.text(x + BW / 2, y + BH + 2.0, title, ha='center', va='bottom',
            fontsize=11.0, fontweight='bold', color=INK)


# ============================== 1. the record ===============================
box(XS[0], BY, '1. Assessor record')
rows = [('recorded floor area', f'{sqft:,.0f} sq ft'),
        ('storeys', f'{storeys}'),
        ('attached garage', f'{garage_sqft:,.0f} sq ft'),
        ('year built', f'{int(r.yr)}')]
cx0 = XS[0] + BW / 2
for i, (k, v) in enumerate(rows):
    yy = BY + BH - 6.5 - i * 11.2
    ax.text(cx0, yy, k, fontsize=7.8, va='center', ha='center', color='0.42')
    ax.text(cx0, yy - 4.2, v, fontsize=9.4, va='center', ha='center',
            color=INK, fontweight='bold')
ax.text(cx0, BY + 3.2, 'no imagery\nof any kind', fontsize=8.0, ha='center',
        va='center', style='italic', color=BOUND_C, linespacing=1.35)

# ============================== 2. the footprint ============================
box(XS[1], BY, '2. Roof footprint')
cx1 = XS[1] + BW / 2
ax.text(cx1, BY + BH - 6.5, f'{sqft:,.0f} \u00f7 {storeys} storeys',
        ha='center', fontsize=8.3, color='0.38')
ax.text(cx1, BY + BH - 12.5, f'= {dwell_m2:,.0f} m\u00b2 dwelling',
        ha='center', fontsize=7.6, color='0.38')
ax.text(cx1, BY + BH - 18.0, f'+ {garage_m2:,.0f} m\u00b2 garage',
        ha='center', fontsize=7.6, color='0.38')
ax.plot([cx1 - 7.5, cx1 + 7.5], [BY + BH - 21.6] * 2, color='0.55', lw=0.9)
ax.text(cx1, BY + BH - 28.0, f'{roof_m2:,.0f} m\u00b2', ha='center', fontsize=15.5,
        fontweight='bold', color=INK)
ax.text(cx1, BY + 5.0, 'roofed ground the\nstructure must occupy',
        ha='center', va='center', fontsize=7.8, color='0.38', linespacing=1.35)

# ============================== 3. the bound ================================
box(XS[2], BY, '3. Physical bound')
cx2 = XS[2] + BW / 2
cs = BW - 7.0
cx, cy = cx2 - cs / 2, BY + BH - 8.0 - cs
ax.add_patch(Rectangle((cx, cy), cs, cs, fc='#f4f6f8', ec='0.45', lw=1.1, zorder=2))
side = cs * np.sqrt(roof_m2 / CELL_M2)
rng = np.random.default_rng(7)
placed = []
for _ in range(n_bldg):
    for _ in range(200):
        px = cx + rng.uniform(0.6, cs - side - 0.6)
        py = cy + rng.uniform(0.6, cs - side - 0.6)
        if all(abs(px - qx) > side * 1.08 or abs(py - qy) > side * 1.08
               for qx, qy in placed):
            placed.append((px, py))
            break
for px, py in placed:
    ax.add_patch(Rectangle((px, py), side, side, fc=BOUND_C, ec='none',
                           alpha=0.85, zorder=3))
ax.text(cx2, cy - 3.2, '30 m cell, 900 m\u00b2', ha='center', fontsize=7.8, color='0.42')
ax.text(cx2, cy - 8.6, f"{len(placed)} recorded roof"
        + ('s' if len(placed) != 1 else '') + ',\nsummed over every\nparcel in the cell',
        ha='center', va='center', fontsize=7.8, color='0.38', linespacing=1.35)
ax.text(cx2, BY + 5.0, f'bound = {bound:.1f}%', ha='center', va='center',
        fontsize=11.6, fontweight='bold', color=BOUND_C)

# ============================== 4. the test =================================
box(XS[3], BY, '4. Test')
cx3 = XS[3] + BW / 2
bw = 4.4
bx = cx3 - 7.6
base = BY + 11.0
top = BY + BH - 15.0
scale = (top - base) / 40.0
ax.add_patch(Rectangle((bx, base), bw, bound * scale, fc=BOUND_C, ec='none', zorder=3))
ax.add_patch(Rectangle((bx + 7.4, base), bw, nlcd * scale, fc=NLCD_C, ec='none', zorder=3))
ax.add_patch(Rectangle((bx + 7.4, base + nlcd * scale), bw, (bound - nlcd) * scale,
                       fc='none', ec=MISS_C, lw=1.2, ls=(0, (2.4, 1.6)), zorder=4))
ax.text(bx + bw / 2, base - 3.0, 'bound', ha='center', va='top',
        fontsize=7.8, color=BOUND_C)
ax.text(bx + 7.4 + bw / 2, base - 3.0, 'NLCD', ha='center', va='top',
        fontsize=7.8, color=NLCD_C)
ax.text(bx + bw / 2, base + bound * scale + 1.2, f'{bound:.1f}%', ha='center',
        fontsize=8.5, color=BOUND_C, fontweight='bold')
ax.text(bx + 7.4 + bw / 2, base + nlcd * scale + 1.2, f'{nlcd:.0f}%', ha='center',
        fontsize=8.5, color=NLCD_C, fontweight='bold')
ax.text(cx3, BY + BH - 7.5, f'{bound - nlcd:.1f} points\nunaccounted', ha='center',
        va='center', fontsize=9.3, color=MISS_C, fontweight='bold', linespacing=1.35)

# ============================== arrows ======================================
LABELS = ['\u00f7 storeys\n+ garage', 'sum in\nthe cell', 'compare']
for k in range(3):
    x_from = XS[k] + BW + 0.35
    x_to = XS[k + 1] - 0.35
    ymid = BY + BH * 0.52
    ax.add_patch(FancyArrowPatch((x_from, ymid), (x_to, ymid), arrowstyle='-|>',
                                 mutation_scale=11, lw=1.1, color='0.45'))
    ax.text((x_from + x_to) / 2, ymid + 4.6, LABELS[k], ha='center', va='center',
            fontsize=6.9, color='0.38', style='italic', linespacing=1.3)

# Two lines: at 11.5 pt bold this title measures 8.04 in against a 7.4 in
# figure, so it is the one title that cannot sit on a single line. It breaks at
# its own comma rather than wherever the width happens to run out.
fig.text(0.5, 0.957,
         'A lower bound built from records rather than imagery,\n'
         'and therefore unable to inherit the occlusion it is used to detect',
         ha='center', va='center', fontsize=11.5, fontweight='bold',
         linespacing=1.25)

# FORMATS AND RESOLUTION
# ----------------------
# This figure is colour LINE ART, so the journal's 1200 dpi tier arguably applies
# rather than the 300 dpi colour tier. The raster ships at 600 dpi and the PDF
# alongside it is fully vector, verified by counting image objects in the PDF: zero.
# The vector form is what actually settles the question; the 600 dpi raster is there
# because PDF is not on the journal's preferred-format list.
#
# The dpi lives in one constant so make_tables.py can read it out of this file and
# check the outputs carry it. All four figure scripts declare DPI the same way; the
# VALUES differ, and Figure 3's 300 is a measured ceiling rather than a lower
# standard. See make_figure_matched_parcels.py.
DPI = 600
# ONE BBOX FOR ALL THREE FORMATS
# ------------------------------
# bbox_inches=_BB is computed per save, and the PDF and Agg renderers measure
# text extents slightly differently, so each format got its own crop. On Figure 3
# that came to a 0.6 percent aspect difference, enough that check_colours.py read
# the PDF as stale against its PNG at 7.7 grey levels on a 6.0 threshold. It was
# not stale: every edge in the frame was displaced by the crop.
#
# The bbox is computed ONCE here and passed to all three saves, so the .pdf, .png
# and .tif of a figure are the same crop rather than three crops inside a
# tolerance. Figure 3's PDF-to-PNG difference fell from 7.71 to 3.4 grey levels.
#
# THE PAD IS 0.1 BECAUSE THAT IS WHAT bbox_inches='tight' USED. It reads as an
# arbitrary constant and is not: matplotlib's savefig.pad_inches default is 0.1, so
# passing an explicit bbox without matching it silently changes the crop. A first
# version of this used 0.02 and took 0.08 inch of white off every side of every
# figure, which is ink within half a millimetre of the file edge and had nothing to
# do with the problem being fixed. Matching 0.1 keeps the shared crop and leaves
# every figure's print width exactly where it was.
_BB = fig.get_tightbbox(fig.canvas.get_renderer()).padded(0.1)
fig.savefig(os.path.join(HERE, 'figure_schematic.pdf'), format='pdf',
            bbox_inches=_BB, facecolor='white')
fig.savefig(os.path.join(HERE, 'figure_schematic.png'), dpi=DPI,
            bbox_inches=_BB, facecolor='white')
fig.savefig(os.path.join(HERE, 'figure_schematic.tif'), dpi=DPI,
            bbox_inches=_BB, facecolor='white', pil_kwargs={'compression': 'tiff_lzw'})
print(f"figure_schematic written; APN {APN}: {sqft:.0f} sqft / {storeys} storeys "
      f"= {dwell_m2:.0f} m2 + {garage_m2:.0f} m2 garage = {roof_m2:.0f} m2 "
      f"= {100*roof_m2/900:.1f}% of the cell; bound {bound:.1f}%, NLCD {nlcd:.0f}%")

def _flatten_tiff(path):
    """Journals want a flat RGB TIFF for production. matplotlib writes RGBA;
    the alpha channel here is uniformly opaque because the figure is saved on a
    white facecolor, so dropping it is lossless and avoids an alpha channel
    reaching the publisher's workflow."""
    from PIL import Image
    im = Image.open(path)
    if im.mode == 'RGBA':
        im.convert('RGB').save(path, compression='tiff_lzw', dpi=(DPI, DPI))

_flatten_tiff(os.path.join(HERE, 'figure_schematic.tif'))
