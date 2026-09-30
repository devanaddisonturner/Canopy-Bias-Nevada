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
Downstream consequence of canopy-driven under-detection of impervious surface.

WHAT THIS IS: an illustrative magnitude calculation, not a calibrated
hydrologic study. It answers one question a reviewer will ask, which is what
an 18 to 22 point impervious understatement actually costs anyone using the
product.

METHOD, standard and published, not invented here:
  NRCS TR-55 composite curve number for connected impervious area
      CN_c = CN_pervious + f * (98 - CN_pervious)
  NRCS runoff equation
      S = 1000 / CN - 10                       (inches)
      Q = (P - 0.2 S)^2 / (P + 0.8 S)          for P > 0.2 S, else 0

CONSERVATISM, and this matters for how the result is read:
  The physical floor is ROOF AREA ONLY. It excludes driveways, walkways and
  patios, which are impervious and which every one of these parcels has. So
  the floor is a LOWER BOUND on true impervious surface, and the runoff gap
  computed against it is a LOWER BOUND on the true runoff error.
  Where NLCD already reports more than the floor, no error is demonstrated,
  so the reference used is max(NLCD, floor) rather than the floor itself.

ASSUMPTIONS, all varied rather than fixed:
  - hydrologic soil group: A, B, C and D are all reported
  - pervious cover: woods in good condition, the correct assumption for
    canopied residential parcels in the Sierra foothills
  - storm depth: 1 to 6 inches, covering roughly the 1-year to 100-year
    24-hour range for western Nevada County
  - antecedent moisture condition II (average), the TR-55 default

    python3 runoff_consequence.py nevada_canopy_bias_rowlevel.csv
"""
import sys
import numpy as np
import pandas as pd

import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
# Default the CSV to this file's own folder, so the script runs from any working
# directory: IDLE's Run Module, a double-click, or an absolute path. Without
# this it dies on FileNotFoundError for a file sitting right beside it.
CSV = sys.argv[1] if len(sys.argv) > 1 else _os.path.join(
    _HERE, 'nevada_canopy_bias_rowlevel.csv')

# TR-55 Table 2-2c, woods in good hydrologic condition, by soil group.
CN_WOODS = {'A': 30, 'B': 55, 'C': 70, 'D': 77}
# TR-55 Table 2-2a, open space in good condition (>75% grass), for comparison.
CN_OPEN = {'A': 39, 'B': 61, 'C': 74, 'D': 80}
CN_IMPERVIOUS = 98.0


def composite_cn(f, cn_perv):
    """TR-55 composite CN for directly connected impervious fraction f."""
    return cn_perv + f * (CN_IMPERVIOUS - cn_perv)


def runoff_in(P, CN):
    """NRCS runoff depth, inches. P is storm depth, inches."""
    S = 1000.0 / CN - 10.0
    Ia = 0.2 * S
    Q = np.where(P > Ia, (P - Ia) ** 2 / (P + 0.8 * S), 0.0)
    return Q


def main():
    d = pd.read_csv(CSV, dtype={'apn': str, 'px': str})
    m = d[(d.yr.notna()) & (d.yr <= 2019)].copy()

    f_nlcd = (m.nlcd / 100.0).clip(0, 1).values
    f_floor = (m.imp_floor_px / 100.0).clip(0, 1).values
    # No error is demonstrated where NLCD already exceeds the roof-only floor.
    f_ref = np.maximum(f_nlcd, f_floor)
    breached = f_floor > f_nlcd

    print(f"\nn = {len(m)} parcels built on or before 2019")
    print(f"mean NLCD impervious fraction            {f_nlcd.mean():.4f}")
    print(f"mean roof-only lower bound               {f_floor.mean():.4f}")
    print(f"mean reference max(NLCD, floor)          {f_ref.mean():.4f}")
    print(f"parcels where NLCD falls below the floor {100*breached.mean():.1f}%")

    print("\n== RUNOFF UNDERSTATEMENT, whole sample ==")
    print("Pervious cover: woods, good condition. Reference is roof area only,")
    print("so every figure below is a LOWER BOUND on the true understatement.\n")
    hdr = f"{'storm':>6} " + ' '.join(f"{'HSG ' + g:>16}" for g in 'ABCD')
    print(hdr)
    print(f"{'(in)':>6} " + ' '.join(f"{'Q_nlcd/Q_ref':>16}" for _ in 'ABCD'))
    for P in (1.0, 2.0, 3.0, 4.0, 6.0):
        cells = []
        for g in 'ABCD':
            cn_p = CN_WOODS[g]
            q1 = runoff_in(P, composite_cn(f_nlcd, cn_p)).mean()
            q2 = runoff_in(P, composite_cn(f_ref, cn_p)).mean()
            ratio = q1 / q2 if q2 > 0 else np.nan
            cells.append(f"{q1:.3f}/{q2:.3f} ={ratio*100:4.0f}%" if q2 > 0
                         else "     n/a       ")
        print(f"{P:>6.1f} " + ' '.join(f"{c:>16}" for c in cells))

    print("\n== BY CANOPY DECILE, soil group B, 3-inch storm ==")
    m['dec'] = pd.qcut(m.canopy, 10, labels=False)
    rows = []
    for k, g in m.groupby('dec'):
        fn = (g.nlcd / 100).clip(0, 1).values
        ff = (g.imp_floor_px / 100).clip(0, 1).values
        fr = np.maximum(fn, ff)
        q1 = runoff_in(3.0, composite_cn(fn, CN_WOODS['B'])).mean()
        q2 = runoff_in(3.0, composite_cn(fr, CN_WOODS['B'])).mean()
        rows.append(dict(decile=k + 1, canopy=g.canopy.mean(),
                         nlcd_imp=100 * fn.mean(), ref_imp=100 * fr.mean(),
                         Q_nlcd=q1, Q_ref=q2,
                         pct_of_true=100 * q1 / q2 if q2 > 0 else np.nan,
                         shortfall_in=q2 - q1))
    t = pd.DataFrame(rows).set_index('decile')
    print(t.round(3).to_string())

    print("\n== SENSITIVITY TO THE PERVIOUS ASSUMPTION (3-inch storm, HSG B) ==")
    for label, table in (('woods, good', CN_WOODS), ('open space, good', CN_OPEN)):
        q1 = runoff_in(3.0, composite_cn(f_nlcd, table['B'])).mean()
        q2 = runoff_in(3.0, composite_cn(f_ref, table['B'])).mean()
        print(f"  {label:<20s} CN_perv={table['B']:>3}  "
              f"Q_nlcd={q1:.3f}  Q_ref={q2:.3f}  "
              f"NLCD captures {100*q1/q2:.0f}% of runoff")

    print("\n== UNACCOUNTED RUNOFF VOLUME, 3-inch storm, HSG B ==")
    for label, g in (('top canopy decile', m[m.dec == 9]),
                     ('all residential parcels in frame', m)):
        fn = (g.nlcd / 100).clip(0, 1).values
        fr = np.maximum(fn, (g.imp_floor_px / 100).clip(0, 1).values)
        short_in = (runoff_in(3.0, composite_cn(fr, CN_WOODS['B'])) -
                    runoff_in(3.0, composite_cn(fn, CN_WOODS['B'])))
        vol_m3 = short_in * 0.0254 * (g.ac.values * 4046.86)
        print(f"  {label:<34s} n={len(g):6d}  "
              f"mean shortfall {short_in.mean():.3f} in  "
              f"total {vol_m3.sum():>9,.0f} m3 = {vol_m3.sum()/1233.5:>6.1f} acre-ft")
    print("  Note this is ONE storm, and only the residential parcels under half")
    print("  an acre that qualify for this frame. It is not a county water budget.\n")

    print("CAVEATS: curve number is an empirical method with wide uncertainty;")
    print("soil group is not mapped here but varied; directly connected")
    print("impervious is assumed; the reference excludes driveways and patios,")
    print("so the true understatement is larger than anything printed above.\n")


if __name__ == '__main__':
    main()
