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
Produce parcel_edge_exact.csv: the distance from each parcel centroid to the
nearest EPSG:5070 30 m cell edge, with the cell indices.

WHY THIS FILE EXISTS SEPARATELY FROM THE RELEASED CSV
-----------------------------------------------------
nevada_canopy_bias_rowlevel.csv carries centroids rounded to four decimal
places, a median position error of about 3.9 m. That is fine for every analysis
in the paper, because the cell assignment `px` was computed upstream at full
precision and is released with the data. It is NOT fine for recomputing cell
geometry, and the cost is measured rather than asserted:

    recomputing the cell indices from the ROUNDED centroids reproduces the
    released pair for 84.33 percent of parcels, against 99.99 percent from full
    precision, and reproduces dedge to within 0.1 m for only 3.20 percent

So this script requires full-precision centroids. It cannot be run against the
released row-level CSV, and it refuses rather than silently producing a file
that is wrong for one parcel in six. `make_tables.py` asserts both figures, so
the claim in this docstring cannot rot.

WHERE TO GET FULL-PRECISION CENTROIDS
-------------------------------------
`run_full_analysis_browser.js` pulls them from the county's ArcGIS REST parcel
service and is the shipped route to the released data. Export its parcel frame
with unrounded `lon` and `lat` and point this script at that file. The county
service is the authority; nothing in this package stores the unrounded values,
which is why the released CSV alone is not sufficient input.

HOW TO RUN
----------
    python3 make_parcel_edge_exact.py full_precision_parcels.csv

The input needs three columns: `apn`, `lon`, `lat`. Output is written beside the
input as parcel_edge_exact.csv, with the columns the released file carries:

    apn        assessor parcel number, twelve digits unformatted
    dedge_dm   centroid-to-nearest-edge distance in decimetres, integer
    i, j       EPSG:5070 30 m cell indices, floor(X/30) and floor(Y/30)
    dedge      the same distance in metres, one decimal place

`px` in the released CSV is these two indices joined as "i_j", which this
script's output reproduces for 99.99 percent of parcels when given full
precision. The residual 0.01 percent is parcels whose centroid sits within
floating-point distance of a cell boundary.

PROVENANCE NOTE
---------------
The original file was produced in an interactive session whose script was not
retained. This is a reconstruction from the documented method, written
2026-09-29. Its arithmetic is verified against the released file: given the
released rounded coordinates it reproduces exactly the 84.33 percent agreement
figure quoted above, which is what the rounding predicts, and the projection it
uses is the same one `make_tables.py::settlement_clustering` recomputes inline
for the 5 km grid. What is NOT verified is an end-to-end run, because the
full-precision input is not in this package. That is stated rather than glossed.
"""
import os
import sys

import numpy as np
import pandas as pd

# EPSG:5070, NAD83 / Conus Albers. GRS80 ellipsoid, standard parallels 29.5 and
# 45.5 N, latitude of origin 23 N, central meridian 96 W, false easting and
# northing both zero. Written out rather than taken from a projection library so
# the package has no geospatial dependency and the arithmetic is auditable.
R, E2 = 6378137.0, 0.0066943800229
LAT0, LON0 = np.radians(23.0), np.radians(-96.0)
P1, P2 = np.radians(29.5), np.radians(45.5)
CELL = 30.0

# Rounding in the released CSV, and what it costs. Both asserted by make_tables.py.
RELEASED_DECIMALS = 4
AGREEMENT_FROM_ROUNDED = 84.33
AGREEMENT_FROM_FULL = 99.99
DEDGE_WITHIN_TENTH_FROM_ROUNDED = 3.20


def albers(lon_deg, lat_deg):
    """Forward EPSG:5070. Returns projected metres (X east, Y north)."""
    def q(t):
        return (1 - E2) * (t / (1 - E2 * t * t) -
                           (1 / (2 * np.sqrt(E2))) *
                           np.log((1 - np.sqrt(E2) * t) / (1 + np.sqrt(E2) * t)))

    def m(t):
        return np.cos(np.arcsin(t)) / np.sqrt(1 - E2 * t * t)

    s1, s2, s0 = np.sin(P1), np.sin(P2), np.sin(LAT0)
    n = (m(s1) ** 2 - m(s2) ** 2) / (q(s2) - q(s1))
    c = m(s1) ** 2 + n * q(s1)
    rho0 = R * np.sqrt(c - n * q(s0)) / n
    la, lo = np.radians(np.asarray(lat_deg, float)), np.radians(np.asarray(lon_deg, float))
    rho = R * np.sqrt(c - n * q(np.sin(la))) / n
    th = n * (lo - LON0)
    return rho * np.sin(th), rho0 - rho * np.cos(th)


def looks_rounded(lon, lat):
    """Is this the released CSV rather than a full-precision export?

    The released coordinates carry exactly four decimals. Guessing from a
    tolerance would misfire on a full-precision export that happens to hold a
    round value, so the test is whether ESSENTIALLY EVERY coordinate is unchanged
    by rounding to four places. A full-precision export fails that immediately.
    """
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    unchanged = ((np.round(lon, RELEASED_DECIMALS) == lon) &
                 (np.round(lat, RELEASED_DECIMALS) == lat))
    return unchanged.mean() > 0.99


def build(df):
    x, y = albers(df.lon.values, df.lat.values)
    i = np.floor(x / CELL).astype(np.int64)
    j = np.floor(y / CELL).astype(np.int64)
    dx = np.minimum(x - i * CELL, (i + 1) * CELL - x)
    dy = np.minimum(y - j * CELL, (j + 1) * CELL - y)
    d = np.minimum(dx, dy)
    return pd.DataFrame({
        'apn': df.apn.astype(str).str.zfill(12),
        'dedge_dm': np.rint(d * 10).astype(np.int64),
        'i': i,
        'j': j,
        'dedge': np.round(d, 1),
    })


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__.strip().split('HOW TO RUN')[1].strip())
    src = sys.argv[1]
    if not os.path.exists(src):
        # A bare filename, resolved against this script's own folder. Someone who
        # drops their full-precision export beside this file and types its name,
        # which is what IDLE's Run Module and a double-click make natural, should
        # not meet a FileNotFoundError for a file that is sitting right there.
        beside = os.path.join(os.path.dirname(os.path.abspath(__file__)), src)
        if os.path.exists(beside):
            src = beside
        else:
            sys.exit('input not found, in the working directory or beside this '
                     'script: %s' % sys.argv[1])
    df = pd.read_csv(src, dtype={'apn': str})
    for col in ('apn', 'lon', 'lat'):
        if col not in df.columns:
            sys.exit('input is missing the %r column; this script needs apn, lon, lat' % col)

    if looks_rounded(df.lon, df.lat):
        sys.exit(
            'REFUSING TO RUN: these coordinates are rounded to %d decimal places.\n'
            '\n'
            'This looks like nevada_canopy_bias_rowlevel.csv, whose centroids carry a\n'
            'median position error of about 3.9 m. Recomputing 30 m cell geometry from\n'
            'them reproduces the released cell indices for only %.2f percent of parcels,\n'
            'against %.2f percent from full precision, so the output would be wrong for\n'
            'roughly one parcel in six while looking entirely plausible.\n'
            '\n'
            'Use a full-precision export from the county parcel service instead; see\n'
            'run_full_analysis_browser.js, and the note at the top of this file.'
            % (RELEASED_DECIMALS, AGREEMENT_FROM_ROUNDED, AGREEMENT_FROM_FULL))

    out = build(df).sort_values('apn').reset_index(drop=True)
    dest = os.path.join(os.path.dirname(os.path.abspath(src)), 'parcel_edge_exact.csv')
    out.to_csv(dest, index=False)
    print('wrote %s, %d rows' % (dest, len(out)))
    print('median centroid-to-edge distance %.2f m' % out.dedge.median())
    print('px equivalent: the i and j columns joined as "i_j"')


if __name__ == '__main__':
    main()
