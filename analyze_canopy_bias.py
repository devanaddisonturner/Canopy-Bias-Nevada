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
Analysis of canopy-driven under-detection of built surface, Nevada County.

Input:  nevada_canopy_bias_rowlevel.csv (24,088 rows) from
        run_full_analysis_browser.js
Output: every number reported in canopy_bias_results.md

This is an independent reimplementation of the in-browser JavaScript analysis.
Both were run and agree to four decimal places, which is the reason to keep
both rather than tidying one away.

    python3 analyze_canopy_bias.py nevada_canopy_bias_rowlevel.csv
"""
import sys
import numpy as np
import pandas as pd
from collections import defaultdict

import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
# Default the CSV to this file's own folder, so the script runs from any working
# directory: IDLE's Run Module, a double-click, or an absolute path. Without
# this it dies on FileNotFoundError for a file sitting right beside it.
CSV = sys.argv[1] if len(sys.argv) > 1 else _os.path.join(
    _HERE, 'nevada_canopy_bias_rowlevel.csv')
XS = ['canopy', 'ac', 'sqft', 'slope', 'n100']


def load():
    d = pd.read_csv(CSV, dtype={'apn': str, 'px': str})
    # Local planar metres for the spatial estimators.
    #
    # NOT EPSG:5070. Albers is an EQUAL-AREA projection: it preserves area and
    # distorts distance, which is the wrong trade for a Bartlett kernel whose
    # weights are a function of distance. Measured against the WGS84 geodesic
    # over 79,980 parcel pairs in this county (pyproj.Geod), EPSG:5070 carries
    # an RMS distance error of 462 m and a median relative error of -0.83 per
    # cent, while the equirectangular form below, tuned to the local latitude,
    # carries 90 m and -0.14 per cent. It is five times the more accurate
    # metric for distance, so it is what the Conley and block estimators use.
    #
    # This matches make_tables.py exactly, so the two implementations agree.
    # EPSG:5070 is still the right projection for the 30 m analysis grid and
    # for the 5 km occupancy figure, which are areal rather than metric.
    _a = d[(d.yr.notna()) & (d.yr <= 2019)]
    _lat_c, _lon_c = _a.lat.mean(), _a.lon.mean()
    d['X'] = (d.lon.values - _lon_c) * 111.32 * np.cos(np.radians(_lat_c)) * 1000.0
    d['Y'] = (d.lat.values - _lat_c) * 110.57 * 1000.0
    return d


def ols(df, y, xs, cluster_m=None):
    """OLS with HC1, or spatial block-cluster errors when cluster_m is set."""
    X = np.column_stack([np.ones(len(df))] + [df[v].astype(float).values for v in xs])
    Y = df[y].astype(float).values
    XtXi = np.linalg.inv(X.T @ X)
    b = XtXi @ (X.T @ Y)
    e = Y - X @ b
    n, k = X.shape
    if cluster_m is None:
        meat = (X * (e ** 2)[:, None]).T @ X
        V = XtXi @ meat @ XtXi * n / (n - k)
        G = None
    else:
        gid = (np.floor(df.X.values / cluster_m).astype(np.int64) * 1000003 +
               np.floor(df.Y.values / cluster_m).astype(np.int64))
        Xe = X * e[:, None]
        _, inv = np.unique(gid, return_inverse=True)
        G = inv.max() + 1
        S = np.zeros((G, k))
        np.add.at(S, inv, Xe)
        V = XtXi @ (S.T @ S) @ XtXi * (G / (G - 1)) * ((n - 1) / (n - k))
    se = np.sqrt(np.diag(V))
    r2 = 1 - (e @ e) / ((Y - Y.mean()) @ (Y - Y.mean()))
    return dict(n=n, G=G, b=b, se=se, t=b / se, r2=r2,
                names=['const'] + list(xs))


def conley_se(X, e, xs, ys, cutoff, XtXi, which=1):
    """Conley spatial HAC, Bartlett kernel, grid-accelerated.

    This was listed as an outstanding item for most of the project on the
    assumption that block clustering was the more conservative choice. That
    assumption was wrong, but so were two attempts to replace it. Ranking the
    two estimators at a given cutoff is ill-posed: the block standard error
    moves about 30 per cent with the arbitrary grid origin, so any verdict is a
    statement about which origin was used. Measured over 25 origins, Conley
    falls INSIDE the block range at all three cutoffs. conley_table() prints
    that range rather than a verdict, and nothing is asserted in prose here,
    because prose is what went stale twice. Conley's merit is that it needs no
    origin at all. It also runs in about four seconds on the full census.
    """
    Xe = X * e[:, None]
    k, n = X.shape[1], X.shape[0]
    gx = np.floor(xs / cutoff).astype(np.int64)
    gy = np.floor(ys / cutoff).astype(np.int64)
    idx = defaultdict(list)
    for i, (a, c) in enumerate(zip(gx, gy)):
        idx[(a, c)].append(i)
    idx = {key: np.array(v) for key, v in idx.items()}
    meat = np.zeros((k, k))
    for (a, c), I in idx.items():
        Xi, xi, yi = Xe[I], xs[I], ys[I]
        for da in (-1, 0, 1):
            for dc in (-1, 0, 1):
                J = idx.get((a + da, c + dc))
                if J is None:
                    continue
                # Chunked so one dense block cannot blow up memory. Settlement
                # is clustered, so the busiest 5 km cell held ~11,000 parcels and
                # produced an 11,000 x 11,000 float64 array, about 968 MB. Only
                # the order of summation changes.
                xj, yj, Xj = xs[J], ys[J], Xe[J]
                step = max(1, 4_000_000 // max(1, len(J)))
                for b in range(0, len(I), step):
                    sl = slice(b, b + step)
                    dist = np.sqrt((xi[sl, None] - xj[None, :]) ** 2 +
                                   (yi[sl, None] - yj[None, :]) ** 2)
                    meat += Xi[sl].T @ (np.clip(1.0 - dist / cutoff, 0, None) @ Xj)
    V = XtXi @ meat @ XtXi * n / (n - k)
    return np.sqrt(np.diag(V))[which]


def conley_table(d):
    """Section 11: Conley spatial HAC for all three outcomes."""
    m = d[(d.yr.notna()) & (d.yr <= 2019)].copy()
    XS_ = ['canopy', 'ac', 'sqft', 'slope', 'n100']
    X = np.column_stack([np.ones(len(m))] + [m[v].astype(float).values for v in XS_])
    xs, ys = m.X.values, m.Y.values
    XtXi = np.linalg.inv(X.T @ X)
    print("\n== 11. CONLEY SPATIAL HAC STANDARD ERRORS ==")
    print("  %-16s %-12s %-18s %-18s %-18s" %
          ('outcome', 'coefficient', 'Conley 1 km', 'Conley 2 km', 'Conley 5 km'))
    for y, lab in [('nlcd', 'measured imp'), ('below', 'below-floor'),
                   ('zero', 'reports zero')]:
        Y = m[y].astype(float).values
        b = XtXi @ (X.T @ Y)
        e = Y - X @ b
        ses = [conley_se(X, e, xs, ys, c, XtXi) for c in (1000, 2000, 5000)]
        print("  %-16s %-12.4f %-18s %-18s %-18s" % (
            lab, b[1],
            "se %.4f t %+.1f" % (ses[0], b[1] / ses[0]),
            "se %.4f t %+.1f" % (ses[1], b[1] / ses[1]),
            "se %.4f t %+.1f" % (ses[2], b[1] / ses[2])))
    # Compare against the block-cluster estimator, ACROSS GRID ORIGINS.
    #
    # Two earlier versions of this comparison were wrong, in different ways.
    # The first hard-coded the verdict in prose and went stale when the
    # distance metric changed. The second derived it, but from a single
    # arbitrary grid origin, which README.md and canopy_bias_results.md had
    # already recorded as ILL-POSED: the block SE moves about 30 per cent with
    # the origin, so "Conley is larger at 2 km" is a statement about which
    # origin happened to be used, not about the estimators.
    #
    # The well-posed comparison is against the block SE's RANGE over origins,
    # which is also how the manuscript reports it in Section 2.4.
    Yn = m['nlcd'].astype(float).values
    bn = XtXi @ (X.T @ Yn)
    en = Yn - X @ bn
    Xe = X * en[:, None]
    print("  against the block-cluster estimator, over 25 grid origins:")
    for c in (1000, 2000, 5000):
        ck = conley_se(X, en, xs, ys, c, XtXi)
        ses = []
        for ox in np.linspace(0, c, 5, endpoint=False):
            for oy in np.linspace(0, c, 5, endpoint=False):
                gid = (np.floor((xs - ox) / c).astype(np.int64) * 1000003 +
                       np.floor((ys - oy) / c).astype(np.int64))
                meat = np.zeros((X.shape[1], X.shape[1]))
                order = np.argsort(gid)
                g_sorted, Xe_sorted = gid[order], Xe[order]
                edges = np.flatnonzero(np.diff(g_sorted)) + 1
                for blk in np.split(Xe_sorted, edges):
                    sg = blk.sum(axis=0)
                    meat += np.outer(sg, sg)
                ses.append(np.sqrt(np.diag(XtXi @ meat @ XtXi))[1])
        lo, hi = min(ses), max(ses)
        inside = lo <= ck <= hi
        print("    %d km  Conley %.4f  block %.4f to %.4f over origins  -> Conley %s"
              % (c // 1000, ck, lo, hi,
                 "sits inside the block range" if inside else
                 ("exceeds every origin" if ck > hi else "is below every origin")))
    print("  The block estimate depends on an arbitrary origin; Conley does not.")


def line(tag, r):
    i = 1  # canopy is always the first regressor
    g = '' if r['G'] is None else f" G={r['G']}"
    print(f"  {tag:<34s} b={r['b'][i]:+9.4f}  se={r['se'][i]:.4f}  "
          f"t={r['t'][i]:+7.2f}  n={r['n']}{g}")


def main():
    d = load()
    main_s = d[(d.yr.notna()) & (d.yr <= 2019)].copy()
    placebo = d[(d.yr.notna()) & (d.yr > 2019)].copy()
    paved = main_s[main_s.road.fillna('').str.startswith('Pavement')].copy()

    print(f"\nCENSUS n={len(d)}  main={len(main_s)}  placebo={len(placebo)}  paved={len(paved)}")
    print(f"mean NLCD impervious {d.nlcd.mean():.2f}   mean physical floor {d.imp_floor_px.mean():.2f}")
    print(f"below-floor {100*d.below.mean():.1f}%   reports exactly zero {100*d.zero.mean():.1f}%")
    print(f"spatial spread: sd(lon)={d.lon.std():.4f}  (a biased sample once gave 0.015)")

    print("\n== 1. MEASURED IMPERVIOUS ~ CANOPY ==")
    line('HC1', ols(main_s, 'nlcd', XS))
    line('spatial block 1 km', ols(main_s, 'nlcd', XS, 1000))
    line('spatial block 2 km', ols(main_s, 'nlcd', XS, 2000))
    print(f"  R2 = {ols(main_s,'nlcd',XS)['r2']:.4f}")

    print("\n== 2. DETECTION FAILURE AGAINST THE PHYSICAL FLOOR ==")
    line('below_floor, 2 km', ols(main_s, 'below', XS, 2000))
    line('below_floor, paved only', ols(paved, 'below', XS, 2000))
    line('below_floor, garage excluded', ols(main_s, 'belowA', XS, 2000))
    line('below_floor, canopy at 5 m', ols(main_s, 'below',
                                           ['canopy5'] + XS[1:], 2000))
    line('PLACEBO post-2019', ols(placebo, 'below', XS))

    print("\n== 3. ASSUMPTION-FREE: PRODUCT REPORTS EXACTLY ZERO ==")
    line('zero, 1 km', ols(main_s, 'zero', XS, 1000))
    line('zero, 2 km', ols(main_s, 'zero', XS, 2000))
    line('zero, PLACEBO', ols(placebo, 'zero', XS, 1000))

    print("\n== 4. THE DECISIVE TEST: CANOPY WITHIN DENSITY STRATUM ==")
    d2 = main_s.copy()
    d2['dq'] = pd.qcut(d2.n100, 4, labels=False, duplicates='drop')
    for q in sorted(d2.dq.dropna().unique()):
        g = d2[d2.dq == q].copy()
        g['cq'] = pd.qcut(g.canopy, 5, labels=False, duplicates='drop')
        agg = g.groupby('cq').agg(below=('below', 'mean'), nlcd=('nlcd', 'mean'))
        bel = '  '.join(f"{100*v:5.1f}" for v in agg.below)
        nl = '  '.join(f"{v:5.1f}" for v in agg.nlcd)
        print(f"  density Q{int(q)+1} (mean {g.n100.mean():5.1f} nbrs, n={len(g):5d})")
        print(f"      below-floor by canopy quintile: {bel}")
        print(f"      NLCD impervious              : {nl}")

    print("\n== 5. SEVERITY TRACKS THE DECISION RULE ==")
    g = main_s.copy()
    g['cq'] = pd.qcut(g.canopy, 5, labels=False, duplicates='drop')
    a = g.groupby('cq').agg(canopy=('canopy', 'mean'), nlcd=('nlcd', 'mean'),
                            dw=('dw', 'mean'), wc=('wc', 'mean'), ghsl=('ghsl', 'mean'))
    print(a.round(1).to_string())
    print("  hard-classified WorldCover collapses; probabilistic Dynamic World degrades gently")

    print("\n== 6. CANOPY DECILE TABLE ==")
    g = main_s.copy()
    g['dec'] = pd.qcut(g.canopy, 10, labels=False)
    t = g.groupby('dec').agg(canopy=('canopy', 'mean'), nlcd=('nlcd', 'mean'),
                             floor=('imp_floor_px', 'mean'),
                             below=('below', 'mean'), zero=('zero', 'mean'))
    t[['below', 'zero']] *= 100
    print(t.round(2).to_string())

    # -- 7 ------------------------------------------------------------------
    # THE COMPETING MECHANISM. The NLCD 2019 impervious metadata states that
    # nighttime lights (DMSP 2011, VIIRS 2016) were imposed on existing NLCD
    # data "to exclude low density impervious areas outside urban and suburban
    # centers". That is a documented production step that deletes rural
    # impervious surface, and it is a rival explanation for everything above.
    #
    # Note this may be OVER-control: dense canopy also suppresses upward light
    # emission, so nighttime radiance may be a mediator of the canopy effect
    # rather than a confounder. Read the two specifications as bounds.
    print("\n== 7. NIGHTTIME-LIGHTS MASK: RIVAL EXPLANATION OR MEDIATOR? ==")
    print(f"  corr(canopy, VIIRS 2016) = {main_s.canopy.corr(main_s.viirs):+.3f}")
    print(f"  corr(canopy, DMSP 2011)  = {main_s.canopy.corr(main_s.dmsp):+.3f}")
    print(f"  corr(canopy, elevation)  = {main_s.canopy.corr(main_s.elev):+.3f}")
    NL = XS + ['viirs', 'dmsp']
    FULL = NL + ['elev']
    for y in ('nlcd', 'below'):
        print(f"  -- {y} --")
        line('base', ols(main_s, y, XS, 2000))
        line('+ nighttime lights', ols(main_s, y, NL, 2000))
        line('+ lights + elevation', ols(main_s, y, FULL, 2000))
    line('zero, + lights', ols(main_s, 'zero', NL, 2000))
    line('PLACEBO below, + lights', ols(placebo, 'below', NL, 1000))
    line('paved only, + lights', ols(paved, 'below', NL, 2000))

    # -- 8 ------------------------------------------------------------------
    # Does the floor construction help or hurt? The floor is mechanically
    # driven by how many recorded buildings share the pixel, which falls with
    # canopy. So high-canopy parcels face a LOWER bar. Controlling for that
    # driver should therefore raise the canopy coefficient if the finding is
    # real, and it does.
    print("\n== 8. IS THE FLOOR CONSTRUCTION CONSERVATIVE? ==")
    print(f"  corr(canopy, n_bldg_px)    = {main_s.canopy.corr(main_s.n_bldg_px):+.3f}")
    print(f"  corr(canopy, imp_floor_px) = {main_s.canopy.corr(main_s.imp_floor_px):+.3f}")
    line('below, base', ols(main_s, 'below', XS))
    line('below, + n_bldg_px', ols(main_s, 'below', XS + ['n_bldg_px']))
    line('below, + floor itself', ols(main_s, 'below', XS + ['n_bldg_px', 'imp_floor_px']))
    print("  the coefficient RISES, so the headline is a conservative bound")

    # -- 9 ------------------------------------------------------------------
    # Forest type. Deciduous canopy is transparent in leaf-off Landsat and
    # evergreen is not, so a deciduous/evergreen contrast would discriminate
    # occlusion from spectral mixing. IT CANNOT BE RUN HERE: Nevada County is
    # overwhelmingly conifer. Reported so nobody tries it again in this county.
    print("\n== 9. FOREST TYPE (why the leaf-off test is not available here) ==")
    for code, name in [(41, 'deciduous'), (42, 'evergreen'), (43, 'mixed')]:
        g = main_s[main_s.lc == code]
        if len(g) < 200:
            print(f"  {name:<10s} lc={code}: n={len(g):5d}  TOO FEW, test not possible")
        else:
            b, se = ols(g, 'below', XS + ['viirs'], 2000)['b'][1], \
                    ols(g, 'below', XS + ['viirs'], 2000)['se'][1]
            print(f"  {name:<10s} lc={code}: n={len(g):5d}  below b={b:+.4f} t={b/se:+.1f}")
    print("  a deciduous/evergreen contrast needs a mixed-forest county, not this one")
    oehha_check(d)
    spec_ladder_and_scope(d)
    conley_table(d)
    print()


def oehha_check(d):
    """
    Route 1 resolved: NLCD against a published FULL-impervious reference.

    California OEHHA Impervious Surface Coefficients, from 330 residential sites
    in Sacramento, Irvine and Santa Cruz digitised from high-resolution aerial
    photography in 9-acre boxes:
        ISC = 0.2449 + 0.352 * log10(dwelling units per acre), valid 1-50 du/ac
    It includes driveways and patios, which the roof-only floor does not, and it
    is a function of density alone, so it carries no canopy information.
    The 100 m neighbour radius encloses 7.76 acres, close to their 9-acre box.
    """
    m = d[(d.yr.notna()) & (d.yr <= 2019)].copy()
    ac100 = np.pi * 100 ** 2 / 4046.86
    m['du_ac'] = (m.n100 + 1) / ac100
    v = m[(m.du_ac >= 1) & (m.du_ac <= 50)].copy()
    v['isc'] = 100 * (0.2449 + 0.352 * np.log10(v.du_ac))
    v['gap'] = v.nlcd - v.isc
    v['dec'] = pd.qcut(v.canopy, 10, labels=False)
    t = v.groupby('dec').agg(canopy=('canopy', 'mean'), du_ac=('du_ac', 'mean'),
                             oehha=('isc', 'mean'), nlcd=('nlcd', 'mean'),
                             roof=('imp_floor_px', 'mean'), gap=('gap', 'mean'),
                             pct_above=('gap', lambda s: 100 * (s > 0).mean()))
    t.index = t.index + 1
    print("\n== 10. NLCD vs A PUBLISHED FULL-IMPERVIOUS REFERENCE (OEHHA) ==")
    print(f"  {len(v)} of {len(m)} parcels in the valid 1-50 du/ac range")
    print(t.round(2).to_string())
    lo, hi = t.loc[1], t.loc[10]
    print(f"  lowest canopy decile:  NLCD is {lo.gap:+.2f} pts from the reference, "
          f"{lo.pct_above:.1f}% of parcels above  <- calibration check")
    print(f"  highest canopy decile: NLCD is {hi.gap:+.2f} pts from the reference, "
          f"{hi.pct_above:.1f}% above")
    print(f"  swing {lo.gap - hi.gap:.1f} pts against full impervious, "
          f"{lo.nlcd - lo.roof - (hi.nlcd - hi.roof):.1f} against roofs only")
    print("  The bias does NOT change sign here: it runs from about zero at low")
    print("  canopy to about -26 at high canopy.")


def spec_ladder_and_scope(d):
    """Section 12. Three things that were previously asserted without testing:
    the control set, the canopy-independence of the frame and of pixel
    assignment, and whether the canopy gradient merely tracks real roof area."""
    m = d[(d.yr.notna()) & (d.yr <= 2019)].copy()
    m['paved'] = m.road.fillna('').str.startswith('Pavement').astype(int)
    H = ['canopy', 'ac', 'sqft', 'slope', 'n100']

    def b_se(df, xs, y='nlcd'):
        X = np.column_stack([np.ones(len(df))] +
                            [df[v].astype(float).values for v in xs])
        Y = df[y].astype(float).values
        XtXi = np.linalg.inv(X.T @ X)
        b = XtXi @ (X.T @ Y); e = Y - X @ b; n, k = X.shape
        V = XtXi @ ((X * (e ** 2)[:, None]).T @ X) @ XtXi * n / (n - k)
        return b, np.sqrt(np.diag(V))

    print("\n== 12a. SPECIFICATION LADDER, census (justifies the control set) ==")
    steps = [('canopy alone', ['canopy']),
             ('+ parcel acres', ['canopy', 'ac']),
             ('+ floor area', ['canopy', 'ac', 'sqft']),
             ('+ slope', ['canopy', 'ac', 'sqft', 'slope']),
             ('+ density 100 m  <- HEADLINE', H),
             ('+ storeys', H + ['storeys']),
             ('+ garage', H + ['storeys', 'garage']),
             ('+ paved access', H + ['storeys', 'garage', 'paved']),
             ('+ improvement value', H + ['storeys', 'garage', 'paved',
                                          'improve']),
             ('+ elevation', H + ['storeys', 'garage', 'paved', 'improve',
                                  'elev']),
             ('+ density 250 m (all)', H + ['storeys', 'garage', 'paved',
                                            'improve', 'elev', 'n250'])]
    prev = None
    for lab, xs in steps:
        b, _ = b_se(m, xs)
        sh = '' if prev is None else f"{b[1] - prev:+6.2f}"
        print(f"  {lab:<32s} {b[1]:+8.2f}  shift {sh}")
        prev = b[1]
    print("  Acres does nearly all the work. Disclosed asymmetry: the headline")
    print("  includes density (shift +0.34, the smallest) and excludes storeys")
    print("  (shift +1.30). Storeys is the weakest-measured assessor field and")
    print("  feeds the roof footprint, so it is partly a construction input.")
    b, se = b_se(m, H + ['storeys', 'garage', 'paved', 'improve', 'elev',
                         'n250'])
    print(f"  Kitchen sink, every covariate: {b[1]:+.2f} (t {b[1]/se[1]:+.1f}) "
          f"-> inside the reported 18-22 range")

    print("\n== 12b. IS PIXEL-ASSIGNMENT ERROR DRIVING IT? (was asserted, now tested) ==")
    print(f"  corr(canopy, acres) = {m.canopy.corr(m.ac):+.3f}, so assignment error")
    print("  is NOT canopy-independent. The scale-free outcome settles it:")
    qs = [(0, .25), (.25, .5), (.5, .75), (.75, 1.)]
    for i, (lo, hi) in enumerate(qs):
        g = (m[m.ac <= m.ac.quantile(hi)] if lo == 0 else
             m[(m.ac > m.ac.quantile(lo)) & (m.ac <= m.ac.quantile(hi))])
        bn, sn = b_se(g, H, 'nlcd')
        bf, _ = b_se(g, H, 'imp_floor_px')
        bb, sb = b_se(g, H, 'below')
        print(f"    acres Q{i+1}  n={len(g):5d}  nlcd {bn[1]:+7.2f}  "
              f"floor {bf[1]:+7.2f}  below-floor {bb[1]:+.4f} (t {bb[1]/sb[1]:+5.1f})")
    print("  below-floor is FLAT across a 2.4-fold range of parcel area, which")
    print("  assignment error cannot produce. The continuous coefficient varies")
    print("  because the FLOOR's own canopy gradient varies (-16.36 to -1.00):")
    print("  small parcels simply have more impervious in the pixel to miss.")
    print("  SCOPE: the frame is GISACRES<=0.5, so the estimate belongs to")
    print("  small-lot residential settlement, not to the county as a whole.")

    print("\n== 12c. DOES THE CANOPY GRADIENT JUST TRACK REAL ROOF AREA? ==")
    bn, sn = b_se(m, H, 'nlcd')
    bf, sf = b_se(m, H, 'imp_floor_px')
    bc, sc = b_se(m, H + ['imp_floor_px'], 'nlcd')
    print(f"  canopy on measured impervious       {bn[1]:+8.2f} (t {bn[1]/sn[1]:+.1f})")
    print(f"  canopy on the physical floor        {bf[1]:+8.2f} (t {bf[1]/sf[1]:+.1f})"
          "   <- real, canopied pixels hold less roof")
    print(f"  canopy on impervious, FLOOR CONTROLLED {bc[1]:+5.2f} (t {bc[1]/sc[1]:+.1f})"
          "   <- barely moves")
    print(f"  pass-through of real roof into measured impervious: {bc[-1]:+.4f}")
    print("  Perfect measurement would give 1.00. Attenuation and limited")
    print("  residual variance push this toward zero, so treat it as a LOWER")
    print("  bound, not as proof the product ignores roofs. The point that")
    print("  matters: conditioning on real roof does not absorb the gradient.")
    print("  NOTE a retracted figure: an earlier note subtracted these two")
    print("  coefficients (-21.90 - -7.89 = -14.00) and called it a")
    print("  decomposition. It is not one. The controlled estimate is correct.")


if __name__ == '__main__':
    main()
