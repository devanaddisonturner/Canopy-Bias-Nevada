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
Figure 1 for the canopy-bias manuscript.

Two assessor-verified residential parcels, matched on everything the analysis
controls for and differing in tree canopy. The pair is NOT chosen by hand: the
selection, the 3,530 candidate matches and the typicality ranking are in
make_tables.py (matched_pair_selection). The panel images come from
gee_matched_parcel_panels.js, run in the Earth Engine code editor. Six panels: aerial imagery, canopy
height and NLCD percent impervious at each site, all over the same 180 m extent.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import matplotlib.patheffects as pe
import numpy as np
import os
import sys
from PIL import Image

# The red markers sit on the green canopy ramp, and the panel they matter most
# in is the closed-canopy one, where that ramp is darkest. Measured against the
# two darkest ramp colours, red separates by 24 and 35 under simulated
# protanopia, and its luminance contrast is 1.30:1 and 2.27:1, both under the
# 3:1 graphics threshold. So the marker was hardest to see in exactly the panel
# the figure exists to show. A white casing restores it by luminance, which is
# unaffected by any colour deficiency and survives greyscale printing. The
# marker itself stays red, which is what the caption calls it.
HALO = [pe.withStroke(linewidth=3.4, foreground='white')]

HERE = os.path.dirname(os.path.abspath(__file__))
# panel images, as written by gee_matched_parcel_panels.js; override with argv[1]
PANELS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'matched_parcel_panels')
OUT = HERE

SERIF = 'Liberation Serif'          # metric-compatible with Times New Roman
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': [SERIF, 'DejaVu Serif'],
    'mathtext.fontset': 'dejavuserif',
})

EXT = [0, 180, 0, 180]             # metres, identical geographic bounds per site


def crop_to_180m(img, lon):
    """Trim each exported panel to the 180 m it is displayed as covering.

    gee_matched_parcel_panels.js asks Earth Engine for Point.buffer(90).bounds(), a
    180 m box, but that box is in EPSG:4326 while the layers are served on the
    EPSG:5070 Albers grid. Albers is rotated with respect to lat/lon by
    theta = n (lambda - lambda0), which is about 14.5 degrees at this
    longitude, so the bounding box of that rotated square in Albers spans
    180 (|cos theta| + |sin theta|), about 219.5 m, not 180 m.

    The panels therefore arrived covering ~219.5 m and were drawn on a 180 m
    axis. Everything in figure units was consequently 21.9 per cent too large
    against the imagery: the 30 m NLCD cell square measured 1.21 pixels across
    rather than 1, and the 50 m scale bars overstated distance by the same
    factor. Measured on the NLCD lattice in the exported panels, the true
    extent is 217 to 221 m, matching the 219.5 m the rotation predicts.

    Cropping centrally to 1/(|cos theta| + |sin theta|) of each side restores
    the stated 180 m. The centroid is at the centre of the export, so a centred
    crop keeps it there.

    ONLY the NLCD panel needs this, and applying it to all three is a mistake
    that was made once here. Earth Engine renders each layer in its own native
    projection. The aerial and canopy panels come back 500 x 390, an aspect of
    1.282, which is dlon/dlat for a 180 m square box at this latitude: they are
    rendered in EPSG:4326, the box's own CRS, so they cover exactly 180 m and
    have non-square pixels in metres, which the common extent and aspect='equal'
    already correct. The NLCD panel comes back 494 x 500, near square, because
    it is rendered on the Albers grid where the rotated box's bounds are square
    and 219.5 m wide. So before this fix the six panels were not co-registered
    at all: four covered 180 m and two covered 219.5 m, all drawn as 180 m.
    """
    n = 0.602903                                   # EPSG:5070 cone constant
    th = np.radians(n * (lon - (-96.0)))
    f = abs(np.cos(th)) + abs(np.sin(th))
    w, h = img.size
    cw, chh = w / f, h / f
    left, top = (w - cw) / 2.0, (h - chh) / 2.0
    out = img.crop((int(round(left)), int(round(top)),
                    int(round(left + cw)), int(round(top + chh))))

    # Verify against the data rather than trusting the arithmetic: NLCD pixels
    # are 30 m, so the lattice period measured in the cropped panel must imply
    # an extent of 180 m, which is what the figure draws it as.
    a = np.asarray(out.convert('L')).astype(int)
    pos = []
    for r in range(3, a.shape[0] - 3, 2):
        v = a[r, :]
        pos += [i for i in range(1, len(v)) if v[i] != v[i - 1]]
    if len(pos) > 50:
        pos = np.array(pos, float)
        # The phase must be searched as well as the period. Fixing it at zero
        # scores every candidate against a lattice that starts at the panel
        # edge, which the real one does not, and returns a period around two
        # thirds of the truth.
        best = None
        for per in np.arange(50, 90, 0.2):
            for ph in np.arange(0, per, 1.0):
                d = np.abs(((pos - ph + per / 2) % per) - per / 2)
                sc = np.mean(np.minimum(d, 3.0))
                if best is None or sc < best[0]:
                    best = (sc, per)
        period = best[1]
        extent = a.shape[1] * 30.0 / period
        assert abs(extent - 180.0) < 6.0, (
            'the cropped NLCD panel spans %.1f m by its own 30 m lattice, but the '
            'figure draws it as 180 m' % extent)
    return out

SITES = [
    dict(key='low', label='Open parcel',
         canopy=4, sqft=1521, ac=0.29, yr=1998, floor=20.5,
         nlcd=38, dw=60, wc=63, apn='040-050-027',
         lat=39.35480, lon=-120.09190, cell=(66.4, 86.3)),
    dict(key='high', label='Canopied parcel',
         canopy=100, sqft=1470, ac=0.29, yr=1998, floor=22.7,
         nlcd=1, dw=16, wc=0, apn='045-300-033',
         lat=39.34660, lon=-120.20670, cell=(65.2, 71.5)),
]

COLS = [
    ('naip_j.jpg', 'Aerial imagery\n(NAIP, 0.6 m, 24 July 2020)', None),
    ('canopy.png', 'Canopy height\n(Meta and WRI, 1 m)', 'canopy'),
    ('imp.png',    'NLCD percent impervious\n(30 m)', 'imp'),
]

CANOPY_PAL = ['#ffffff', '#e8f3e0', '#b7dba0', '#74c476', '#31a354', '#006d2c', '#00441b']
IMP_PAL    = ['#f7f7f7', '#d9d9d9', '#bdbdbd', '#969696', '#636363', '#252525']

fig = plt.figure(figsize=(7.2, 6.45), dpi=300)
gs = fig.add_gridspec(2, 3, left=0.075, right=0.985, top=0.905, bottom=0.215,
                      wspace=0.055, hspace=0.06)

panel_letters = [['a', 'b', 'c'], ['d', 'e', 'f']]

for r, site in enumerate(SITES):
    for c, (suffix, coltitle, kind) in enumerate(COLS):
        ax = fig.add_subplot(gs[r, c])
        img = Image.open(os.path.join(PANELS, f"{site['key']}_{suffix}"))
        # Only the NLCD panel needs it; see crop_to_180m.
        if kind == 'imp':
            img = crop_to_180m(img, site['lon'])
        ax.imshow(np.asarray(img), extent=EXT, aspect='equal',
                  interpolation='nearest' if kind == 'imp' else 'bilinear')
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_linewidth(0.6); s.set_color('0.25')

        # parcel centroid marker
        ax.plot(90, 90, marker='+', ms=11, mew=1.6,
                color='#d62728', zorder=5, path_effects=HALO)
        ax.plot(90, 90, marker='o', ms=15, mfc='none', mew=1.0,
                color='#d62728', zorder=5, path_effects=HALO)

        # 30 m NLCD cell reference square, centred on the parcel
        if kind == 'imp':
            cx, cy = site['cell']
            ax.add_patch(Rectangle((cx, cy), 30, 30, fill=False,
                                   ec='#d62728', lw=1.4, ls='-', zorder=4,
                                   path_effects=HALO))

        # column heading
        if r == 0:
            ax.set_title(coltitle, fontsize=8.2, pad=5)

        # panel letter
        ax.text(0.028, 0.965, f"({panel_letters[r][c]})", transform=ax.transAxes,
                fontsize=8.5, fontweight='bold', va='top', ha='left', color='white',
                bbox=dict(boxstyle='square,pad=0.22', fc='black', ec='none', alpha=0.62))

        # scale bar on the first panel of each row
        if c == 0:
            ax.plot([12, 62], [14, 14], color='white', lw=2.6, solid_capstyle='butt', zorder=6)
            ax.plot([12, 62], [14, 14], color='black', lw=1.2, solid_capstyle='butt', zorder=7)
            ax.text(37, 20, '50 m', ha='center', va='bottom', fontsize=7,
                    color='white', zorder=7,
                    bbox=dict(boxstyle='square,pad=0.12', fc='black', ec='none', alpha=0.55))

        # the reported value, stated on the panel it comes from
        if kind == 'imp':
            ax.text(0.5, 0.055, f"NLCD reports {site['nlcd']}%",
                    transform=ax.transAxes, ha='center', va='bottom', fontsize=8.6,
                    fontweight='bold', color='black',
                    bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='0.4', lw=0.6, alpha=0.93))
        if kind == 'canopy':
            ax.text(0.5, 0.055, f"cover above 2 m: {site['canopy']}%",
                    transform=ax.transAxes, ha='center', va='bottom', fontsize=8.6,
                    color='black',
                    bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='0.4', lw=0.6, alpha=0.93))

    # row label on the left
    axfirst = fig.axes[-3]
    axfirst.set_ylabel(f"{site['label']}\nAPN {site['apn']}",
                       fontsize=8.2, labelpad=6, linespacing=1.35)

# ---- colour bars under columns 2 and 3 -------------------------------------
cax1 = fig.add_axes([0.385, 0.163, 0.255, 0.016])
cmap1 = mcolors.LinearSegmentedColormap.from_list('canopy', CANOPY_PAL)
cb1 = fig.colorbar(cm.ScalarMappable(norm=mcolors.Normalize(0, 30), cmap=cmap1),
                   cax=cax1, orientation='horizontal')
cb1.set_label('canopy height (m); label gives cover fraction above 2 m', fontsize=6.6, labelpad=1.5)
cb1.ax.tick_params(labelsize=6.6, length=2, pad=1)
cb1.outline.set_linewidth(0.5)

cax2 = fig.add_axes([0.695, 0.163, 0.255, 0.016])
cmap2 = mcolors.LinearSegmentedColormap.from_list('imp', IMP_PAL)
cb2 = fig.colorbar(cm.ScalarMappable(norm=mcolors.Normalize(0, 60), cmap=cmap2),
                   cax=cax2, orientation='horizontal')
cb2.set_label('percent impervious', fontsize=7.2, labelpad=1.5)
cb2.ax.tick_params(labelsize=6.6, length=2, pad=1)
cb2.outline.set_linewidth(0.5)

# ---- the comparison, stated as text ----------------------------------------
lo, hi = SITES
line1 = (f"Matched pair. Open parcel: {lo['sqft']:,} sq ft dwelling on {lo['ac']} ac, built {lo['yr']}; "
         f"recorded roof occupies {lo['floor']}% of the 30 m cell.   "
         f"Canopied parcel: {hi['sqft']:,} sq ft on {hi['ac']} ac, built {hi['yr']}; roof occupies {hi['floor']}%.")
line2 = (f"NLCD reports {lo['nlcd']}% and {hi['nlcd']}% impervious respectively. "
         f"Dynamic World {lo['dw']} and {hi['dw']}; ESA WorldCover {lo['wc']}% and {hi['wc']}%. "
         f"The canopied cell falls {hi['floor'] - hi['nlcd']:.1f} points below its physical lower bound.")
fig.text(0.5, 0.098, line1, ha='center', va='top', fontsize=7.1, linespacing=1.4)
fig.text(0.5, 0.055, line2, ha='center', va='top', fontsize=7.1, linespacing=1.4)

# Not italic. This was the only figure title in italic, which read as an aside
# rather than as the figure's claim, and it was also the smallest at 9.2 pt.
fig.text(0.5, 0.968,
         'Two dwellings of near-identical size, lot and age; opposite canopy; opposite measurement outcome',
         ha='center', va='center', fontsize=11.5, fontweight='bold')

# legend for the markers
handles = [
    Line2D([], [], marker='+', color='#d62728', ls='none', ms=8, mew=1.6,
           path_effects=HALO, label='parcel centroid'),
    Line2D([], [], marker='s', mfc='none', mec='#d62728', ls='none', ms=8, mew=1.2,
           path_effects=HALO, label='30 m NLCD cell'),
]
fig.legend(handles=handles, loc='lower left', bbox_to_anchor=(0.075, 0.150),
           frameon=False, fontsize=7.0, handletextpad=0.5, labelspacing=0.32)

# FORMATS AND RESOLUTION
# ----------------------
# A PDF is emitted so that all four figures offer the same three formats, but be
# clear about what it is: unlike Figures 1, 2 and 4, whose PDFs are vector, this
# one carries the six Earth Engine panel exports as embedded 633x633 rasters. It is
# a raster in a PDF wrapper. Send the TIFF.
#
# THE 300 DPI HERE IS NOT A COMPROMISE, IT IS THE CEILING. Measured: the grid spans
# (0.985 - 0.075) x 7.2 = 6.552 in across three panels with wspace=0.055, so each
# panel prints 2.1068 in wide. The source exports are 633 px, so 633 / 2.1068 = 300.5 dpi.
# A 300 dpi save renders each panel at 632 px, a one-pixel match to its
# input. A 600 dpi save would render it at 1264 px from a 633 px source: double the
# bytes and not one additional pixel of real detail.
#
# So this figure stays at 300 while Figure 1 was raised to 600. The difference is
# not inconsistency, it is that Figure 1 is drawn and has no ceiling, and this one
# is photographic and has one. Re-derive this arithmetic before changing the dpi.
DPI = 300
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
fig.savefig(os.path.join(OUT, 'figure_matched_parcels.pdf'), format='pdf',
            bbox_inches=_BB, facecolor='white')
fig.savefig(os.path.join(OUT, 'figure_matched_parcels.png'), dpi=DPI,
            bbox_inches=_BB, facecolor='white')
fig.savefig(os.path.join(OUT, 'figure_matched_parcels.tif'), dpi=DPI,
            bbox_inches=_BB, facecolor='white', pil_kwargs={'compression': 'tiff_lzw'})
print('figure written')

def _flatten_tiff(path):
    """Journals want a flat RGB TIFF for production. matplotlib writes RGBA;
    the alpha channel here is uniformly opaque because the figure is saved on a
    white facecolor, so dropping it is lossless and avoids an alpha channel
    reaching the publisher's workflow."""
    from PIL import Image
    im = Image.open(path)
    if im.mode == 'RGBA':
        im.convert('RGB').save(path, compression='tiff_lzw', dpi=(DPI, DPI))


_flatten_tiff(os.path.join(OUT, 'figure_matched_parcels.tif'))
