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
Divergence figure. What the physical bound requires against what the product
reports, across the canopy range. This figure replaces the canopy-decile table:
it carries the same four series and shows the thing a table cannot, which is
that the two curves cross and then separate.

    python3 make_figure_divergence.py [nevada_canopy_bias_rowlevel.csv]

Writes PNG and LZW TIFF at 300 dpi.
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'nevada_canopy_bias_rowlevel.csv')

SERIF = 'Liberation Serif'
plt.rcParams.update({'font.family': 'serif', 'font.serif': [SERIF, 'DejaVu Serif']})

d = pd.read_csv(CSV, dtype={'apn': str, 'px': str})
m = d[(d.yr.notna()) & (d.yr <= 2019)].copy()
m['dec'] = pd.qcut(m.canopy, 10, labels=False)
# a cell cannot be more than wholly impervious: truncate the bound at 100 per cent.
# binds on 163 parcels in 33 cells where a structure larger than one cell is charged
# in full to the cell holding its centroid.
m['bound_t'] = m.imp_floor_px.clip(upper=100)
m['below_t'] = (m.nlcd < m.bound_t)
g = m.groupby('dec').agg(canopy=('canopy', 'mean'), bound=('bound_t', 'mean'),
                         bound_sd=('bound_t', 'std'), nlcd=('nlcd', 'mean'),
                         nlcd_sd=('nlcd', 'std'), below=('below_t', 'mean'),
                         zero=('zero', 'mean'), n=('nlcd', 'size'))
# 95 per cent confidence intervals on each decile mean
CI = 1.96
g['e_bound'] = CI * g.bound_sd / np.sqrt(g.n)
g['e_nlcd'] = CI * g.nlcd_sd / np.sqrt(g.n)
g['e_below'] = 100 * CI * np.sqrt(g.below * (1 - g.below) / g.n)
g['e_zero'] = 100 * CI * np.sqrt(g.zero * (1 - g.zero) / g.n)
x = g.canopy.values
bound, nlcd = g.bound.values, g.nlcd.values

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
GAP_C = '#6B0F1A'      # gap annotation: arrow and label
FILL_C, FILL_A = '#d62728', 0.16   # shaded deficit band, before compositing
BOUND_C = '#1A4A78'
NLCD_C = '#D06A10'

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 4.85), dpi=300)
fig.subplots_adjust(left=0.082, right=0.985, top=0.885, bottom=0.105, wspace=0.235)

# ---------------- (a) the two series -----------------------------------------
# shade the region where the product reports LESS than the bound requires
ax1.fill_between(x, nlcd, bound, where=(bound >= nlcd), interpolate=True,
                 color=FILL_C, alpha=FILL_A, zorder=1,
                 label='reported below the physical bound')
ax1.fill_between(x, nlcd, bound, where=(bound < nlcd), interpolate=True,
                 color='0.55', alpha=0.15, zorder=1)

ax1.errorbar(x, bound, yerr=g.e_bound.values, fmt='-o', color=BOUND_C, lw=2.0,
             ms=5.0, capsize=2.4, elinewidth=0.9, capthick=0.9, zorder=3,
             label='physical lower bound (recorded roof)')
ax1.errorbar(x, nlcd, yerr=g.e_nlcd.values, fmt='-s', color=NLCD_C, lw=2.0,
             ms=5.0, capsize=2.4, elinewidth=0.9, capthick=0.9, zorder=3,
             label='NLCD measured impervious')

# mark the crossing
cross = [i for i in range(9) if (nlcd[i] - bound[i]) * (nlcd[i+1] - bound[i+1]) < 0]
if cross:
    i = cross[0]
    t = (bound[i] - nlcd[i]) / ((nlcd[i+1] - nlcd[i]) - (bound[i+1] - bound[i]))
    xc = x[i] + t * (x[i+1] - x[i])
    yc = nlcd[i] + t * (nlcd[i+1] - nlcd[i])
    ax1.plot([xc], [yc], marker='o', ms=8, mfc='none', mec='0.25', mew=1.1, zorder=5)
    ax1.annotate('series cross', xy=(xc, yc), xytext=(xc + 0.10, yc + 9),
                 fontsize=8.2, color='0.25',
                 arrowprops=dict(arrowstyle='-', color='0.45', lw=0.7,
                                 shrinkA=0, shrinkB=7))

gap = bound[-1] - nlcd[-1]
ax1.annotate('', xy=(x[-1], bound[-1]), xytext=(x[-1], nlcd[-1]),
             arrowprops=dict(arrowstyle='<->', color=GAP_C, lw=1.1))
ax1.text(x[-1] - 0.035, (bound[-1] + nlcd[-1]) / 2, f'{gap:.1f} pts',
         fontsize=8.4, color=GAP_C, ha='right', va='center', fontweight='bold')

ax1.set_xlabel('canopy cover above 2 m (decile mean)', fontsize=9.4)
ax1.set_ylabel('percent of 30 m cell', fontsize=9.4)
ax1.set_ylim(0, 44)
ax1.tick_params(labelsize=8.6)
ax1.legend(fontsize=8.0, loc='lower left', frameon=False, handlelength=2.0,
           labelspacing=0.35, borderpad=0.2)
ax1.set_title('(a) what must be there, and what is reported',
              fontsize=9.6, pad=6, loc='center')
for s in ax1.spines.values():
    s.set_linewidth(0.7)
ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)

# ---------------- (b) the two failure rates ----------------------------------
ax2.errorbar(x, 100 * g.below.values, yerr=g.e_below.values, fmt='-o',
             color='#d62728', lw=1.7, ms=5.0, capsize=2.4, elinewidth=0.9,
             capthick=0.9, label='reports less than the bound')
ax2.errorbar(x, 100 * g.zero.values, yerr=g.e_zero.values, fmt='-^',
             color='#7b3294', lw=1.7, ms=5.2, capsize=2.4, elinewidth=0.9,
             capthick=0.9, label='reports exactly zero')
ax2.set_xlabel('canopy cover above 2 m (decile mean)', fontsize=9.4)
ax2.set_ylabel('percent of parcels', fontsize=9.4)
ax2.set_ylim(0, 92)
ax2.tick_params(labelsize=8.6)
ax2.legend(fontsize=8.0, loc='upper left', frameon=False, handlelength=2.0,
           labelspacing=0.35, borderpad=0.2)
ax2.set_title('(b) detection failure', fontsize=9.6, pad=6, loc='center')
for s in ax2.spines.values():
    s.set_linewidth(0.7)
ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)

fig.text(0.5, 0.962,
         'The bound falls gently with canopy. What the product reports falls nearly twice as fast.',
         fontsize=11.5, fontweight='bold', va='center', ha='center')
# The confidence-interval note that used to sit here was removed: it crowded
# the centred panel titles and repeated the caption word for word, which
# already states the error bars and what they cover.

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
fig.savefig(os.path.join(HERE, 'figure_divergence.pdf'), format='pdf',
            bbox_inches=_BB, facecolor='white')
fig.savefig(os.path.join(HERE, 'figure_divergence.png'), dpi=DPI,
            bbox_inches=_BB, facecolor='white')
fig.savefig(os.path.join(HERE, 'figure_divergence.tif'), dpi=DPI,
            bbox_inches=_BB, facecolor='white', pil_kwargs={'compression': 'tiff_lzw'})
print(f"figure_divergence written; bound {bound[0]:.1f}->{bound[-1]:.1f}, "
      f"NLCD {nlcd[0]:.1f}->{nlcd[-1]:.1f}, final gap {gap:.1f} points")

def _flatten_tiff(path):
    """Journals want a flat RGB TIFF for production. matplotlib writes RGBA;
    the alpha channel here is uniformly opaque because the figure is saved on a
    white facecolor, so dropping it is lossless and avoids an alpha channel
    reaching the publisher's workflow."""
    from PIL import Image
    im = Image.open(path)
    if im.mode == 'RGBA':
        im.convert('RGB').save(path, compression='tiff_lzw', dpi=(DPI, DPI))

_flatten_tiff(os.path.join(HERE, 'figure_divergence.tif'))
