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
Study area figure. Nevada County, California: the 21,931 analysed parcels,
their canopy cover, and the two parcels illustrated in Figure 3.

    python3 make_figure_studyarea.py [nevada_canopy_bias_rowlevel.csv]

Boundaries come from figure_boundaries.json, pulled from TIGER/2018 via Earth
Engine; see figure_boundaries_gee.js. Writes PNG and LZW TIFF at 300 dpi.
"""
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe

# Site markers are red and sit on a green canopy ramp. Red on dark green is the
# classic red-green confusion, and here it is worse than that: #d62728 against
# the darkest ramp colour separates by only 8 under simulated protanopia and
# carries 1.30:1 luminance contrast, so it fails the 3:1 graphics threshold for
# every reader and vanishes in greyscale. A white casing under the marker fixes
# it for all readers at once, because the marker is then found by a luminance
# step of 6.5 to 11.4:1 against the dark greens, which no colour deficiency
# affects. The marker stays red, as the figure captions describe it.
HALO = [pe.withStroke(linewidth=3.6, foreground='white')]

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'nevada_canopy_bias_rowlevel.csv')

SERIF = 'Liberation Serif'
plt.rcParams.update({'font.family': 'serif', 'font.serif': [SERIF, 'DejaVu Serif']})

geo = json.load(open(os.path.join(HERE, 'figure_boundaries.json'), encoding='utf-8'))
nev = np.array(geo['nevada'])
ca = np.array(geo['california'])

d = pd.read_csv(CSV, dtype={'apn': str, 'px': str})
m = d[(d.yr.notna()) & (d.yr <= 2019)].copy()

SITES = [dict(lon=-120.09190, lat=39.35480, tag='open'),
         dict(lon=-120.20670, lat=39.34660, tag='canopied')]

lat0 = m.lat.mean()
# true local shape: km per degree latitude over km per degree longitude
ASPECT = 110.57 / (111.32 * np.cos(np.radians(lat0)))

fig = plt.figure(figsize=(7.2, 5.35), dpi=300)
ax = fig.add_axes([0.055, 0.335, 0.925, 0.585])

ax.plot(nev[:, 0], nev[:, 1], color='0.25', lw=1.1, zorder=3)

cmap = mcolors.LinearSegmentedColormap.from_list(
    'canopy', ['#f2f2f0', '#cfe3c2', '#8fca86', '#3f9c46', '#10612a'])
order = np.argsort(m.canopy.values)          # draw high canopy last
sc = ax.scatter(m.lon.values[order], m.lat.values[order], c=m.canopy.values[order],
                cmap=cmap, vmin=0, vmax=1, s=1.1, linewidths=0, alpha=0.85, zorder=2)

for s in SITES:
    ax.plot(s['lon'], s['lat'], marker='o', ms=7, mfc='none', mec='#d62728',
            mew=1.6, zorder=6, path_effects=HALO)
ax.legend(handles=[Line2D([], [], marker='o', ls='none', ms=6, mfc='none',
                          mec='#d62728', mew=1.5, path_effects=HALO,
                          label='parcels illustrated in Figure 3')],
          loc='upper left', bbox_to_anchor=(0.015, 0.985), frameon=False,
          fontsize=8.4, handletextpad=0.6)

ax.set_aspect(ASPECT)
ax.set_xlim(nev[:, 0].min() - 0.03, nev[:, 0].max() + 0.03)
ax.set_ylim(nev[:, 1].min() - 0.03, nev[:, 1].max() + 0.05)
# graticule: a map without coordinates is not a map
xt = np.arange(-121.2, -120.0 + 0.001, 0.3)
yt = np.arange(39.1, 39.5 + 0.001, 0.2)
ax.set_xticks(xt); ax.set_yticks(yt)
ax.set_xticklabels([f'{abs(v):.1f}\u00b0W' for v in xt], fontsize=8.0)
ax.set_yticklabels([f'{v:.1f}\u00b0N' for v in yt], fontsize=8.0)
ax.tick_params(length=2.5, width=0.6, pad=2)
for gx in xt:
    ax.axvline(gx, color='0.85', lw=0.4, zorder=0)
for gy in yt:
    ax.axhline(gy, color='0.85', lw=0.4, zorder=0)
for sp in ax.spines.values():
    sp.set_linewidth(0.6); sp.set_color('0.35')

# scale bar, 20 km, drawn in degrees of longitude at this latitude
km = 20.0
dx = km / (111.32 * np.cos(np.radians(lat0)))
x0, y0 = nev[:, 0].min() + 0.03, nev[:, 1].min() + 0.055
ax.plot([x0, x0 + dx], [y0, y0], color='black', lw=2.2, solid_capstyle='butt', zorder=8)
ax.text(x0 + dx / 2, y0 + 0.020, f'{km:.0f} km', ha='center', fontsize=8.2, zorder=8)
ax.annotate('N', xy=(nev[:, 0].max() - 0.02, nev[:, 1].max() + 0.005),
            ha='center', fontsize=10.0, zorder=8)
ax.annotate('', xy=(nev[:, 0].max() - 0.02, nev[:, 1].max() + 0.005),
            xytext=(nev[:, 0].max() - 0.02, nev[:, 1].max() - 0.035),
            arrowprops=dict(arrowstyle='-|>', color='black', lw=0.9), zorder=8)

cax = fig.add_axes([0.655, 0.115, 0.30, 0.024])
cb = fig.colorbar(sc, cax=cax, orientation='horizontal')
cb.set_label('canopy cover above 2 m (fraction)', fontsize=8.4, labelpad=2)
cb.ax.tick_params(labelsize=7.8, length=2.5, pad=1.5)
cb.outline.set_linewidth(0.5)
cb.set_alpha(1)

# ---- California inset ------------------------------------------------------
ins = fig.add_axes([0.055, 0.025, 0.155, 0.235])
ins.plot(ca[:, 0], ca[:, 1], color='0.35', lw=0.8)
ins.fill(nev[:, 0], nev[:, 1], color='#d62728', zorder=3)
ins.plot(nev[:, 0], nev[:, 1], color='#d62728', lw=1.6, zorder=4)
ins.set_aspect(ASPECT)
ins.set_xticks([]); ins.set_yticks([])
for sp in ins.spines.values():
    sp.set_linewidth(0.5); sp.set_color('0.5')
ins.text(0.5, -0.06, 'California', transform=ins.transAxes, ha='center',
         va='top', fontsize=8.6)

# ---- the numbers that motivate the spatial standard errors ----------------
span_ew = (m.lon.max() - m.lon.min()) * 111.32 * np.cos(np.radians(lat0))
span_ns = (m.lat.max() - m.lat.min()) * 110.57
# 5 km cells on the EPSG:5070 Albers grid, the same grid the caption and the
# verification harness use. A 0.05 degree graticule was used here previously,
# which is 4.3 km east to west and 5.5 km north to south at this latitude and
# so is not a 5 km cell.
_R, _e2 = 6378137.0, 0.0066943800229
_lat0, _lon0 = np.radians(23.0), np.radians(-96.0)
_p1, _p2 = np.radians(29.5), np.radians(45.5)
_q = lambda t: (1 - _e2) * (t / (1 - _e2 * t * t) -
                            (1 / (2 * np.sqrt(_e2))) *
                            np.log((1 - np.sqrt(_e2) * t) / (1 + np.sqrt(_e2) * t)))
_mm = lambda t: np.cos(np.arcsin(t)) / np.sqrt(1 - _e2 * t * t)
_s1, _s2, _s0 = np.sin(_p1), np.sin(_p2), np.sin(_lat0)
_n = (_mm(_s1) ** 2 - _mm(_s2) ** 2) / (_q(_s2) - _q(_s1))
_C = _mm(_s1) ** 2 + _n * _q(_s1)
_rho0 = _R * np.sqrt(_C - _n * _q(_s0)) / _n
_rho = _R * np.sqrt(_C - _n * _q(np.sin(np.radians(m.lat.values)))) / _n
_th = _n * (np.radians(m.lon.values) - _lon0)
_X, _Y = _rho * np.sin(_th), _rho0 - _rho * np.cos(_th)
m['_c'] = list(zip(np.floor(_X / 5000.0), np.floor(_Y / 5000.0)))
top5 = m['_c'].value_counts().head(5).sum()
txt = (f"{len(m):,} parcels, built on or before 2019\n"
       f"spanning {span_ew:.0f} km east to west and {span_ns:.0f} km north to south\n"
       f"clustered, not dispersed: five of {m['_c'].nunique()} occupied 5 km cells\n"
       f"hold {100*top5/len(m):.0f} percent of them")
fig.text(0.255, 0.255, txt, fontsize=8.6, va='top', ha='left', linespacing=1.6)

fig.text(0.5, 0.962, 'Nevada County, California: the analysed parcels and their canopy',
         ha='center',
         fontsize=11.5, fontweight='bold', va='center')

# FORMATS AND RESOLUTION, corrected 29 September 2026
# --------------------------------------------------
# This figure shipped at 300 dpi with no PDF, on the reasoning that it is
# "photographic raster content, where 300 dpi for colour is the journal's
# requirement". That reasoning was wrong: this figure draws everything except its
# colourbar. The scatter, the county outline, the labels and the inset are drawn, which
# makes this line or combination art, the class the journal rates at 1200 dpi
# rather than 300.
#
# Measured rather than assumed. Saving this figure as a PDF and counting image
# XObjects gives exactly ONE, a 648x38 greyscale alpha mask belonging to the
# colourbar. The 21,931-point scatter is vector. So the vector PDF genuinely
# resolves the resolution question for this figure, which is more than can be said
# for Figure 3, whose PDF carries six 633x633 rasters.
#
# So: 600 dpi to match Figures 2 and 4, and a vector PDF alongside. The three
# formats are now the same three for every one of the four figures.
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
fig.savefig(os.path.join(HERE, 'figure_studyarea.pdf'), format='pdf',
            bbox_inches=_BB, facecolor='white')
fig.savefig(os.path.join(HERE, 'figure_studyarea.png'), dpi=DPI,
            bbox_inches=_BB, facecolor='white')
fig.savefig(os.path.join(HERE, 'figure_studyarea.tif'), dpi=DPI,
            bbox_inches=_BB, facecolor='white', pil_kwargs={'compression': 'tiff_lzw'})
print('figure_studyarea written')

def _flatten_tiff(path):
    """Journals want a flat RGB TIFF for production. matplotlib writes RGBA;
    the alpha channel here is uniformly opaque because the figure is saved on a
    white facecolor, so dropping it is lossless and avoids an alpha channel
    reaching the publisher's workflow."""
    from PIL import Image
    im = Image.open(path)
    if im.mode == 'RGBA':
        im.convert('RGB').save(path, compression='tiff_lzw', dpi=(DPI, DPI))

_flatten_tiff(os.path.join(HERE, 'figure_studyarea.tif'))
