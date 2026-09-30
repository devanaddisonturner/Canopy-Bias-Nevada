# Licence: the decision, and why the alternatives were not chosen

*Devan Cantrell Addison-Turner, ORCID [0000-0002-2511-3680](https://orcid.org/0000-0002-2511-3680), Department of Civil and Environmental Engineering, Stanford University. From the reproduction package for "An optically independent administrative reference for validating built-surface products, and the tree-canopy bias it reveals", prepared for GIScience & Remote Sensing. Repository: https://github.com/devanaddisonturner/Canopy-Bias-Nevada Code MIT, released data CC0 1.0.*

**Status: decided and in force.** `LICENSE` is present at the repository root,
`CITATION.cff` names the licence, and the README states both halves. This file
records the reasoning, because a licence choice a reuser cannot see the reasoning
for is one they have to guess at.

Nothing here is legal advice. The one item genuinely outside this file's scope is
named at the end.

## The decision

**Code under the MIT License. Data separately dedicated to the public domain
under CC0 1.0.** Stated separately because they are different kinds of thing and
one licence should not be asked to cover both.

CC0 covers `nevada_canopy_bias_rowlevel.csv`, `parcel_edge_exact.csv`,
`parcel_extras.csv`, `ms_footprint_validation.csv`, `ca_county_scan.csv` and
`nlcd_vs_ghsl_check.csv`. MIT covers the extraction scripts, the analysis, the
figure scripts and the verification harness.

## Why MIT and not Apache-2.0

Apache-2.0 adds three things over MIT: an express patent grant from
contributors, a patent-retaliation termination clause, and obligations to
preserve `NOTICE` files and to state changes made.

Only the patent grant is a real consideration, and it has nothing to operate on
here. Apache-2.0's grant works by binding *contributors* to license the patents
they hold that their contribution practises. This is a single-author package with
no patent filed and no patent application pending, so there is no such patent to
grant and the clause is inert. Whether anything in the method could in principle
be patented is a question for a patent attorney and is deliberately not answered
here; the point is only that the clause changes nothing today. Against that,
Apache-2.0 is a longer licence and imposes notice-preservation and
change-statement obligations on anyone reusing a single figure script.

Apache-2.0 would be the better choice if a patent on the method were in
prospect, or if the repository expected outside contributors whose patent rights
a user would want granted forward. Neither applies to a single-author
reproduction package accompanying one paper.

BSD-3-Clause was also considered. It is MIT plus a no-endorsement clause, is
common in the scientific Python world, and is functionally equivalent in
practice. It offers no advantage here and is less universally recognised than
MIT.

## Why not CC BY-NC, or any NonCommercial licence

Four reasons, in order of weight.

**1. The NonCommercial restriction defeats the purpose of the paper.** The
argument is that four widely used built-surface products under-measure impervious
surface where a building provably exists, and that anyone relying on them for
stormwater regulation or equity assessment should be able to check. The audience
is therefore consultancies running stormwater assessments, water utilities,
municipal staff and analysts. "NonCommercial" is famously undefined at exactly
that boundary: a consultancy is commercial, a private utility probably is, a
university with industry funding is arguable. An NC licence tells precisely the
readers who most need to verify this that they may not.

An NC licence is also **not open** by the two standard definitions. The Open
Source Definition's sixth criterion reads: "The license must not restrict anyone
from making use of the program in a specific field of endeavor. For example, it
may not restrict the program from being used in a business." The Open Definition
takes the same position. So NC code could not be described as open source in the
paper or anywhere else.

*Scope note, corrected 29 September 2026.* An earlier draft of this file asserted
that NC would forfeit the journal's **Open Materials badge**. That does not
follow and is withdrawn. The badge criteria require the materials to be in an
open-access repository, described in enough detail to reproduce the procedure, and
say nothing about licence terms. An unlicensed repository is a problem, because it
is all rights reserved by default; a NonCommercial one is a problem for the three
reasons given here, not because of the badge.

**2. Creative Commons recommends against CC licences for software.** That is
CC's own published position, not a preference expressed here. CC licences do not
address source versus object code, say nothing about patent rights, and do not
handle distribution of modifications. For code they are the wrong instrument
regardless of which clauses are attached.

**3. On the data specifically, NC would contradict a published statement and
overclaim.** The manuscript's data availability statement already commits the
dataset to CC0. Changing it to BY-NC would put the repository at odds with the
paper. And the inputs are public-domain government records: county assessor
rolls, NLCD, TIGER. Asserting a NonCommercial restriction over a derivative of
public-domain records is a weak position to take and an unattractive one.

**4. NC does not achieve what it is usually reached for.** The instinct behind it
is to stop someone profiting from the work. It does not do that: it deters
good-faith reuse while bad-faith reuse ignores licences. And it adds nothing to
attribution, which BY already requires and which `CITATION.cff` plus the version
DOI handle properly. If the concern is credit, the citation file is the
instrument, not the licence.

A copyleft licence such as GPL-3.0 was considered and rejected for a milder
version of reason 1: it restricts the downstream reuse this package exists to
invite.

## What this unblocked

An unlicensed repository is **all rights reserved** by default, so nobody could
legally reuse it. Having the licence in place is what allows the Zenodo deposit,
which requires a licence at upload and which the journal requires at or before
submission, and what supports the Open Materials badge.

## The one thing outside this file's scope

University policy can bear on the licensing of research code. Stanford's
technology-licensing office is the right place to confirm that nothing in this
work is subject to an institutional interest before the repository goes public.
That is a question for them and not one any file here can answer.

## The three places the licence is written, which must agree

1. `LICENSE` at the repository root, carrying the MIT text and the CC0
   dedication for the named datasets.
2. `CITATION.cff`'s `license:` field, as the SPDX identifier `MIT`.
3. The README's "Licence and citation" section, stating both halves.

`make_tables.py` checks that a `LICENSE` file and a licence in `CITATION.cff`
exist together, and that this file does not describe the decision as still open
while `LICENSE` is present.
