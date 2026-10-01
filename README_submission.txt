SUBMISSION PACKAGE
An optically independent administrative reference for validating built-surface
products, and the tree-canopy bias it reveals
Devan Cantrell Addison-Turner, ORCID 0000-0002-2511-3680
Department of Civil and Environmental Engineering, Stanford University

Target: GIScience & Remote Sensing (Taylor & Francis)
Editor in Chief: Prof. Jungho Im
Assembled 30 September 2026

=====================================================================
THE DOI IS IN. NO PLACEHOLDER REMAINS IN THE MANUSCRIPT.
=====================================================================

The Data availability statement now reads "The dataset and code are deposited at
https://doi.org/10.5281/zenodo.23072749." That VERSION DOI was reserved on
30 September 2026 before these files were built, so the archive deposited at it
states its own DOI rather than saying one is still to be assigned.

The journal's requirement is met: "Data must be deposited in a recognized
FAIR-aligned data repository PRIOR TO OR AT THE TIME OF SUBMISSION." Give the
same string in the submission form's DOI field.

Run this before uploading, and expect exit 0:

    python3 check_layout.py --submission

It exits 0 and reports "no bracketed placeholders remain". Run it anyway. A
manuscript submitted with "[insert the DOI here]" still in it is the kind of
error no reviewer forgives, and this is the check that catches a regression.

WHAT TO UPLOAD, IN ORDER
------------------------
The numbered folders are the submission, in the order a submission form asks for
them. One file per slot, no choices to make.

  01_Manuscript/    canopy_bias_manuscript_GIScienceRS.docx
                    The manuscript. 23 pages. The journal offers format-free
                    submission, so it needs no reformatting.

  02_Cover_letter/  COVER_LETTER.docx
                    One page, addressed to Prof. Im. Some systems take the letter
                    as pasted text instead; the wording is the same either way.

  03_Figures/       Figure1.tif, Figure1.pdf, Figure2.tif, Figure2.pdf,
                    Figure3.tif, Figure3.pdf, Figure4.tif, Figure4.pdf,
                    GraphicalAbstract1.png
                    Upload the four TIFFs and the graphical abstract. The PDFs are
                    there in case a production editor asks for a vector form, which
                    for Figures 1, 2 and 4 is what they are. See README_figures.txt
                    in that folder for dpi, dimensions, why Figure 1 is 600 dpi
                    while Figure 3 is 300, and why there is no EPS.

  Reference_renderings_do_not_upload/
                    canopy_bias_manuscript_GIScienceRS.pdf
                    COVER_LETTER.pdf
                    PDF renderings of the manuscript and the cover letter. These
                    are here so you can see exactly what the .docx files produce
                    before you upload them. THEY ARE NOT SUBMISSION FILES. Most
                    systems want one main document, and uploading the PDF as the
                    manuscript is the way to end up with two versions of record.

NOT IN THIS ZIP, ON PURPOSE
---------------------------
The reproduction package, canopy_bias_reproduction_package.zip, 71 files. It is
not a submission attachment: it is what gets DEPOSITED IN ZENODO, at the DOI
already named above. It is also on GitHub at
https://github.com/devanaddisonturner/Canopy-Bias-Nevada. See
GITHUB_AND_ZENODO.md inside that package for the steps.

BEFORE YOU UPLOAD
-----------------
1. Publish the Zenodo deposit if it is still a draft. The DOI is reserved rather
   than registered until you press Publish, and a reserved DOI does not resolve.
   Attach the rebuilt reproduction package, the one whose files name the DOI, not
   a copy made before it existed. Give the same DOI in the submission form.
2. Confirm which Heinz organisation funded the work. The Funding statement
   currently reads "The Heinz Foundations", which is not the formal name of any
   Heinz philanthropy. The two candidates are The Heinz Endowments and the Heinz
   Family Foundation, and the same string is in the BMJ Open protocol.
3. Check the editor is still Prof. Jungho Im. This could not be verified
   automatically because the publisher blocks it; the name comes from the
   Instructions for Authors PDF dated 14 September 2026.
4. Settle the article publishing charge BEFORE submitting. It is $3,565 plus VAT
   on a fully open access journal, Stanford Libraries lists no Taylor & Francis
   agreement, and the guidelines say waivers "may not be considered after
   submission". Declaring who funded the research is not the same as arranging
   who pays the charge.

TWO QUESTIONS RAISED AND NOT DECIDED
------------------------------------
- WOEIP, S4CA and OUSD are acknowledged in the BMJ Open protocol and are NOT
  acknowledged here, because their involvement was with the EJT education trial
  rather than with this measurement study. If any of them contributed to this
  paper, the acknowledgement should be restored.
- The protocol declares a competing interest, a provisional patent on EJT
  methodology (Stanford OTL docket S25-565). This manuscript declares none. That
  is very likely right, since the patent covers EJT computational methods, but
  the two documents say different things about the same author's interests.

IF YOU EDIT ANYTHING, REBUILD THE RENDERINGS
--------------------------------------------
The .docx files are built from source (build_manuscript.js, build_cover_letter.js)
and the PDFs are converted from the .docx. Editing a source without rebuilding
leaves a rendering behind its source, which is a defect this project has hit
before. Both are gated: make_tables.py checks the manuscript .docx, the manuscript
.pdf, the cover letter .docx and the cover letter .pdf against their sources on
every run, so a divergence fails rather than ships. File timestamps are NOT a
reliable signal here and pointed the wrong way at assembly time; trust the harness.

Then rebuild this zip, with build_submission.sh in the reproduction package. It
assembles this archive and the figures archive from the working tree behind the
same three gates, and rereads them afterwards. Until 29 September 2026 both were
assembled by hand, and this file said the reproduction package held 65 files when
it held 64: the number came off the summary line of `unzip -l`, which counts the
matched_parcel_panels/ directory entry as a file. Nothing checked it. The
archive gate in make_tables.py now reads this file back out of the built zip and
checks its file count, its assertion counts, and every figure dimension and dpi
stated in README_figures.txt against the images actually in the archive.

VERIFICATION STATE AT ASSEMBLY
------------------------------
522 assertions pass in the working tree and from a clean unzip of the reproduction
package, 517 with SciPy and statsmodels absent. Layout clean at 23 pages, Figure 1
on page 3, Table 4 on page 16. Colour legible under all three dichromacies and
greyscale. All 13 checksums verify. The independent R reimplementation agrees.

The four TIFFs in 03_Figures were confirmed pixel-identical to the images embedded
in the manuscript in this zip, so the figures a reviewer downloads separately and
the figures inside the paper are the same images. No image in this zip or in the
reproduction package carries an embedded C2PA content-credentials manifest; the
harness rescans all fifteen on every run, and it reads the nine figure files back out
of this zip and compares them to the working tree, so a figure regenerated after
the zip was built fails rather than reaching a reviewer. Six of the fifteen went
unscanned until 29 September 2026 and all six carried one; see CHECKSUMS.sha256 in
the reproduction package for what they claimed and what was done about it.
