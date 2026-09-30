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
"""Graphical abstract for GIScience & Remote Sensing.

The journal asks for a maximum width of 525 pixels, saved as .jpg, .png or
.tiff, not embedded in the manuscript, and labelled GraphicalAbstract1. It is
optional; the journal's own figures say articles carrying an extender such as
a graphical abstract are markedly more likely to be downloaded.

Designed for 525 pixels, not shrunk down from a print figure: one message,
two series, large type, no tick clutter. Every number is computed from the
released row-level data, so it cannot drift from the manuscript.

    python3 make_graphical_abstract.py [nevada_canopy_bias_rowlevel.csv]
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

plt.rcParams.update({'font.family': 'serif',
                     'font.serif': ['Liberation Serif', 'DejaVu Serif']})

d = pd.read_csv(CSV, dtype={'apn': str, 'px': str})
m = d[(d.yr.notna()) & (d.yr <= 2019)].copy()
m['bound'] = m.imp_floor_px.clip(upper=100)          # the bound is truncated at a full cell
m['dec'] = pd.qcut(m.canopy, 10, labels=False)
g = m.groupby('dec').agg(canopy=('canopy', 'mean'), bound=('bound', 'mean'), nlcd=('nlcd', 'mean'))
x, b, n = g.canopy.values, g.bound.values, g.nlcd.values
gap = b[-1] - n[-1]
n_parcels = len(m)

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
FILL_C, FILL_A = '#d62728', 0.17   # shaded deficit band, before compositing
BOUND_C, NLCD_C = '#1A4A78', '#D06A10'
W_PX, H_PX, DPI = 525, 388, 100
fig = plt.figure(figsize=(W_PX / DPI, H_PX / DPI), dpi=DPI)
# left is set so the plot block, which carries the y label and ticks on its
# left but nothing on its right, sits centred on the canvas as drawn ink.
ax = fig.add_axes([0.113, 0.2797, 0.825, 0.525])

ax.fill_between(x, n, b, where=(b >= n), interpolate=True, color=FILL_C, alpha=FILL_A, zorder=1)
ax.plot(x, b, '-o', color=BOUND_C, lw=2.2, ms=4.0, zorder=3,
        label='minimum the assessor records require')
ax.plot(x, n, '-s', color=NLCD_C, lw=2.2, ms=4.0, zorder=3,
        label='what the satellite product reports')

ax.annotate('', xy=(x[-1], b[-1]), xytext=(x[-1], n[-1]),
            arrowprops=dict(arrowstyle='<->', color=GAP_C, lw=1.2))
# The gap label sits inside the shaded band. Three lines did not fit: the band
# is 12.1 units deep at the right edge but shallower where the text extends
# left, so the last line landed on the lower curve and its foot was clipped.
# Two lines fit, and the position is computed from the curves rather than
# guessed, then asserted.
LBL_RIGHT = x[-1] - 0.03
LBL_W = 0.120                      # measured width of the wider line, in x units
LBL_LEFT = LBL_RIGHT - LBL_W
_ax_h_in = 0.525 * H_PX / DPI
_units_per_in = 44.0 / _ax_h_in
GAP_FS = 8.6
_half = 1.0 * GAP_FS * 1.25 / 72 * _units_per_in   # half of a two-line block
# clearance is judged where the text actually reaches, not at the right edge
_lo = max(np.interp(LBL_LEFT, x, n), n[-1]) + 0.6 + _half
_hi = min(np.interp(LBL_LEFT, x, b), b[-1]) - 0.4 - _half
assert _lo < _hi, 'no room for the gap label inside the shaded band'
LABEL_Y = (_lo + _hi) / 2
ax.text(LBL_RIGHT, LABEL_Y, f'{gap:.1f} points\nmissing',
        fontsize=GAP_FS, color=GAP_C, ha='right', va='center',
        fontweight='bold', linespacing=1.25, clip_on=False, zorder=5)

ax.set_xlabel('tree canopy cover above 2 m (fraction)', fontsize=8.6, labelpad=2)
ax.set_ylabel('percent of a 30 m cell', fontsize=8.6, labelpad=3)
ax.set_ylim(0, 44)
ax.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
ax.tick_params(labelsize=7.6, length=3, pad=2)
ax.legend(fontsize=7.6, loc='lower left', frameon=False,
          handlelength=1.7, labelspacing=0.25, borderpad=0.1)
for s in ax.spines.values():
    s.set_linewidth(0.8)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# The title was lowered on 29 September at the author's request, from 0.878 to
# 0.860, so the block sits nearer the plot than the top edge and reads as a
# heading attached to the figure rather than a banner floating above it.
#
# That exposed a separate problem and made it worse. Measured on the rendered
# pixels, the composition had 33 px of white above it and 11 below; lowering the
# title took the top margin to 40 and left the whole thing 14.5 px below centre.
# Horizontally it was already centred to half a pixel, which is what the offset
# axes box exists to achieve, so only the vertical needed correcting.
#
# The fix moved the title, the axes and the footnote up by the SAME 14 px, so
# every internal gap was preserved exactly. Shifting only the title would have
# undone the request.
#
# Lowered once more on the same day, and the two goals pull against each other,
# so both are handled at once. The title alone drops 8 px within the header
# band, closing the title-to-panel gap from 26 px to 18. That alone would push
# the composition 4.5 px below centre again, because the top of the ink IS the
# top of the title, so the whole block is then lifted 4.5 px to rebalance.
#
# Net: the title sits 3.5 px lower on the canvas, the panel and footnote 4.5 px
# higher, the gap above the title and below the footnote stay equal, and the
# title reads as attached to the plot rather than floating in the header band.
# Measured on the rendered pixels, not computed from these fractions.
# The earlier title said canopy "hides" buildings. That is a causal, agentive
# verb, and the paper disclaims causation: "It is not a demonstration that
# canopy causes it ... the language throughout is associational." This wording
# is descriptive and names the reference the paper contributes.
fig.text(0.5, 0.8871, 'Under closed canopy, optical products report\nless impervious surface than records require',
         fontsize=10.4, fontweight='bold', va='center', ha='center', linespacing=1.25)
fig.text(0.5, 0.0757,
         f'{n_parcels:,} parcels with a recorded dwelling, Nevada County, California. That minimum needs\n'
         'two fields of the county assessor property record, recorded floor area and storey count.\n'
         'It uses no imagery, so it cannot inherit the occlusion it is used to detect.',
         fontsize=7.0, color='0.25', va='bottom', ha='center', linespacing=1.32)

# The title must stay associational, matching the manuscript.
_title = 'Under closed canopy, optical products report less impervious surface than records require'
for _v in ('hides', 'obscures', 'blocks', 'conceals', 'causes', 'prevents'):
    assert _v not in _title.lower(), f'causal verb "{_v}" in a title the paper does not support'

out = os.path.join(HERE, 'GraphicalAbstract1.png')
fig.savefig(out, dpi=DPI, facecolor='white')
from PIL import Image
im = Image.open(out)
assert im.size[0] <= 525, 'graphical abstract exceeds the 525 pixel width limit'
print(f'GraphicalAbstract1.png written, {im.size[0]}x{im.size[1]} px '
      f'(limit 525 wide); gap {gap:.1f} points, n = {n_parcels:,}')
