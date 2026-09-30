FIGURE FILES
GIScience & Remote Sensing submission
Canopy bias in built-surface products, Nevada County, California
Devan Cantrell Addison-Turner, ORCID 0000-0002-2511-3680
Department of Civil and Environmental Engineering, Stanford University
Assembled 30 September 2026

WHAT IS HERE
------------
  Figure1.tif   4035 x 3283 px   600 dpi   6.72 in wide   Study area
  Figure1.pdf   vector, 1 colourbar raster               same figure
  Figure2.tif   4440 x 3089 px   600 dpi   7.40 in wide   Construction of the bound
  Figure2.pdf   fully vector                             same figure
  Figure3.tif   2344 x 1875 px   300 dpi   7.81 in wide   Matched-pair parcels
  Figure3.pdf   6 raster objects                         same figure
  Figure4.tif   4259 x 2890 px   600 dpi   7.10 in wide   Bound against measured
  Figure4.pdf   fully vector                             same figure
  GraphicalAbstract1.png 525 x 388 px                    graphical abstract

File names are the manuscript's figure numbers, verified against the captions in
the manuscript source rather than assumed. Every dpi and pixel dimension above
was read from the file's own tags, not restated from a note, and so was every
raster-object count in the PDF column.

WHY THESE FORMATS
-----------------
All four figures ship the same three formats, .tif, .png and .pdf. Until
29 September 2026 Figures 1 and 3 had no PDF, which made the set look like a
judgement about those two figures when for Figure 1 it was a mistake.

**Figure 1 was misclassified and has been raised.** It was described as
"photographic raster content" and shipped at 300 dpi. It holds no photographic
content at all: the scatter, the county outline, the inset and the type are drawn.
Saving it as a PDF and counting image objects gives exactly one, a 648 x 39 greyscale
colourbar strip; the 21,931-point scatter is vector. That makes it line or
combination art, the class the journal rates at 1200 dpi rather than 300, and it
is now 600 dpi with a vector PDF alongside, matching Figures 2 and 4.

One qualification, measured rather than glossed: that colourbar strip is placed at
2.160 x 0.130 in from a 648 x 39 px source, which is 300 dpi. So Figure 1's PDF is
vector everywhere except a colourbar carried at 300. That is the right tier for it
rather than a shortfall, because a colourbar is a smooth continuous-tone gradient
and 300 dpi for colour is exactly what that tier is for. It is line art that the
1200 dpi rule would bear on, and there is none of it in that strip.

**Figure 3 stays at 300 dpi, and that is a ceiling rather than a concession.** Its
grid spans 6.552 in across three panels, so each panel prints 2.107 in wide, and
the Earth Engine exports behind them are 633 px. 633 / 2.1068 = 300.5 dpi. A
300 dpi save renders each panel at 632 px, within a pixel of its input. A 600 dpi
save would render 1264 px from a 633 px source: twice the bytes and not one extra
pixel of real detail. Its PDF carries those six exports as embedded rasters, so it
is a raster in a PDF wrapper and gains nothing over the TIFF.

ONE CROP PER FIGURE, NOT THREE
------------------------------
The three files for a figure are now the same crop. They were not before. Each
save computed its own tight bounding box, and the PDF and raster renderers measure
text extents slightly differently, so every figure's PDF was a fractionally
different crop from its PNG. On Figure 3 that reached a 0.6 percent aspect
difference, which displaced every edge in the frame and made check_colours.py read
the PDF as stale against its PNG at 7.7 grey levels against a 6.0 threshold. It was
not stale. The bounding box is computed once per figure and passed to all three
saves; Figure 3's PDF-to-PNG difference fell to 3.7 and every figure's fell or held.
The pad is 0.1 inch, which is what bbox_inches='tight' used, so the dimensions
above are unchanged by this fix. A first attempt passed 0.02 and quietly took
0.08 inch of white off every side of every figure, putting ink within half a
millimetre of the file edge. Matching matplotlib's own default was the point.

So the dpi differs between Figure 1 and Figure 3 for a measured reason. The
arithmetic is in the comments at the foot of each figure script, and make_tables.py
reads the dpi each script asks for and checks the files carry it.

To be precise about what the PDFs are for, since it is easy to overstate: the
journal's preferred figure formats are PS, JPEG, TIFF and Word, and PDF is not
among them, so the TIFF is the compliant submission file in every case and the PDF
is insurance against a production editor classifying a colour line drawing as line
art and asking for 1200 dpi. Send the TIFFs. Offer the PDFs if asked, and for
Figures 1, 2 and 4 they answer the question properly because they are vector.
Figure 3's does not.

DO NOT CONVERT THESE TO EPS
---------------------------
PostScript is on the journal's preferred-format list, so exporting EPS looks like
the safe move. It is not. The PostScript backend does not support transparency
and renders partially transparent artists opaque, without raising an error.
Figure 4's shaded confidence band is the entire point of that panel and becomes a
solid block over the curves; Figure 2's tinted panel flattens the same way. The
failure is silent and survives visual inspection at thumbnail size. Use the TIFFs
or the PDFs.

THE GRAPHICAL ABSTRACT
----------------------
Submitted as a separate file, not embedded in the manuscript. It is 525 px wide,
the journal's maximum, and was designed at that size rather than shrunk from a
print figure. It is generated from the released row-level data by
make_graphical_abstract.py, so it cannot drift from the manuscript: the 12.1
point gap and the 21,931 sample size it prints are both asserted by the
verification harness.

It is a PNG only. There is deliberately no .tif and no .pdf, and the reason is
that the graphical abstract is governed by a different rule from the figures
above. The guidelines say of it: "It should be a maximum width of 525 pixels. If
your image is narrower than 525 pixels, please place it on a white background 525
pixels wide ... Save the graphical abstract as a .jpg, .png, or .tif." That is a
PIXEL rule, because the graphical abstract is a listing thumbnail rather than
print artwork, and a vector PDF has no pixel width to satisfy it with. PDF is also
absent from those three permitted formats. A .tif would be permitted, but .png is
on the same list, is lossless, is the size the image was designed at, and the
guidelines say to label the file GraphicalAbstract1, singular: two files under
that name would leave a production editor guessing which one is the graphical
abstract. All four of those rules are now gated by make_tables.py rather than
left as prose, including that a GraphicalAbstract1.pdf would fail.

PROVENANCE
----------
All five images are regenerated by their scripts in the reproduction package and
reproduce pixel for pixel. None carries an embedded C2PA content-credentials
manifest. That is not a claim made once at assembly. make_tables.py rescans every
shipped image on every run, and it now reads these nine files back out of this
zip and compares them to the working tree, so a figure regenerated after the zip
was built fails rather than reaching a reviewer. Working PNG masters are in the
reproduction package alongside the scripts that make them.
