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
import numpy as np
from collections import defaultdict
def conley_se(X, e, xs, ys, cutoff, XtXi, which=1):
    """Conley spatial HAC, Bartlett kernel, grid-accelerated."""
    Xe = X*e[:,None]; k = X.shape[1]; n = X.shape[0]
    gx=np.floor(xs/cutoff).astype(np.int64); gy=np.floor(ys/cutoff).astype(np.int64)
    idx=defaultdict(list)
    for i,(a,c) in enumerate(zip(gx,gy)): idx[(a,c)].append(i)
    idx={key:np.array(v) for key,v in idx.items()}
    meat=np.zeros((k,k))
    for (a,c),I in idx.items():
        Xi=Xe[I]; xi=xs[I]; yi=ys[I]
        for da in (-1,0,1):
            for dc in (-1,0,1):
                J=idx.get((a+da,c+dc))
                if J is None: continue
                # Chunked: one dense block per cell pair peaked near 1 GB on
                # this frame, where five of 47 occupied cells hold half the
                # parcels. Only the summation order changes.
                xj,yj,Xj=xs[J],ys[J],Xe[J]
                step=max(1,4_000_000//max(1,len(J)))
                for b in range(0,len(I),step):
                    sl=slice(b,b+step)
                    dist=np.sqrt((xi[sl,None]-xj[None,:])**2+(yi[sl,None]-yj[None,:])**2)
                    meat+=Xi[sl].T@(np.clip(1.0-dist/cutoff,0,None)@Xj)
    V=XtXi@meat@XtXi*n/(n-k)
    return np.sqrt(np.diag(V))[which]
