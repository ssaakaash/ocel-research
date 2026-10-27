# Publishing the flattening paper: status and steps

Paper: *What Does Flattening Hide? Measuring Case-Notion Distortion and Its Consequences on Seven Real Object-Centric Event Logs* (draft v0.4).
Source text: `docs/research/Journal_Manuscript_Draft.md`. Submission file: `Manuscript_v0.4.docx` (v0.3 files kept for comparison) (rebuild with `scripts/review3/build_manuscript_docx.py`).
Nothing has been submitted anywhere. Every step below that sends something outside the team is yours to do.

## 1. Where the paper stands

Done:
- Written fresh on the real-data study. No synthetic data, no portal data.
- Every number comes from `realdata/results`; the three tables are printed by `scripts/review3/make_paper_tables.py`.
- Checked in parts by independent code: SQL, brute-force directly-follows and entity ranking, raw-file recomputation, and (new) a plain-Python version of the distortion metrics that agrees on 60 case notions across slices of three logs. `make study` re-runs everything and leaves tracked results unchanged.
- References re-checked on 2026-10-27 against publisher, arXiv, DBLP or index records. Corrections made: [4] (BPM 2023 Workshops, pp. 496-507), [6] (full author list, article 15), [7], [9], [10], [11] (article numbers and DOIs).
- Declarations section, three figures, three tables, line-numbered A4 Word file.
- v0.4: narrowing reframed around plausible case notions (widest notion per log; notions covering at least half the events), threshold sensitivity added (printed by `make_paper_tables.py`), log selection explained, tone made more formal.

Still open before you submit (you need to supply or decide):
| Item | Why it blocks |
|---|---|
| Affiliations, corresponding author, ORCID iDs | Every system asks; highlighted yellow on the title page |
| Author list and order, and whether your guide is a co-author | Needs your guide's consent; decide before upload |
| CRediT contributions per author | Highlighted in Declarations |
| Generative-AI use statement | Most publishers require it. Write what you actually did. A starting point is below |
| Reference [1] page range, [4] year, whether [5] is now in a journal | Springer pages blocked our check; confirm on the publisher page |
| Code licence and public repository | See step 5. The paper's data-availability sentence points at it |
| Venue choice and its Scopus status | Your outcome form asks for a Scopus-indexed journal; check the live Scopus Sources list |

Suggested AI-use statement (edit so it is true for you): "During the preparation of this work the authors used Claude (Anthropic) to help draft and edit the text, to write parts of the analysis and document-generation code, and to run checks. The authors reviewed and edited the output and take full responsibility for the content."

## 2. What a reviewer is likely to say (fix the first three if you can)

1. **Too short and too few references.** The main text is about 1,900 words with 11 references. Full journal articles in this area are longer and cite far more. Add a proper related-work section (OCEL 1.0 and the OCEL 2.0 tooling, other object-centric extraction and flattening work, event-log quality, educational process mining) using only references you have opened and checked.
2. **Seven logs, no statistics.** Done in v0.4: threshold sensitivity and the log-selection rule are now in the paper. Reviewers may still ask for more logs.
3. **No independent labelling and no full-log second implementation.** Run `check_distortion.py` on full logs where memory allows, and ask someone outside the team to check the findings table.
4. **Practical value.** Show the three rules in section 5 on one worked example (Enron is already in the report).
5. **Novelty.** The metrics restate known issues. The contribution is the cross-log measurement and the duplication-versus-narrowing split. Say that in the cover letter without claiming more.

## 3. Choosing a venue (facts as found on 2026-10-27; verify before relying on them)

| Venue | Fit and facts | Check yourself |
|---|---|---|
| **Process Science** (Springer; flagship of the Process Science Association, run by the BPM Conference steering committee and the IEEE Task Force on Process Mining) | Best topical fit. Fully gold open access, article processing charge due at acceptance, waivers possible. Single-blind review. States a target of a first decision within a month and bimonthly deadlines. Published [6], so it covers object-centric data quality | Scopus indexing (we could not confirm it), the current charge, article types and length limits, preprint policy |
| **Decision Analytics Journal** (Elsevier, ISSN 2772-6622) | Published [7]. Gold open access with an article charge. One index record lists Scopus and DOAJ coverage | Charge, whether a measurement paper fits its analytics scope, current Scopus status |
| **ICPM** (International Conference on Process Mining) | The 2027 edition (8-12 Feb 2027, Rende) had its paper deadline in early September 2026, so it has passed. Research papers are up to 13 pages, published open access in the ACM ICPS series. Worth targeting next year | Official call page for the next edition |
| Object-centric workshops at BPM or ICPM | The OBJECTS workshop series ran with BPM 2026. No 2027 call was found | Watch the BPM 2027 and ICPM 2027 workshop calls |

A journal that is not on Scopus will not satisfy the Scopus line of your outcome form. Open the journal's entry in the Scopus Sources list and look at its status and coverage dates. Avoid venues that email you first, promise very fast acceptance, or charge a fee at submission.

## 4. Steps to get the paper reviewed

1. **Agree the plan with your guide.** Decide authorship (and whether the guide is corresponding author), the target journal, and who pays the charge if there is one (ask about waivers and any VIT support).
2. **Check the venue.** Open its Springer or Elsevier page and read the author guidelines: article types, length, formatting, whether LaTeX or Word, review model, charges, preprint and AI-use rules. Confirm Scopus status.
3. **Strengthen the paper** (section 2 above). Change `Journal_Manuscript_Draft.md`, then rebuild the Word file: `realdata/.venv/bin/python scripts/review3/build_manuscript_docx.py`.
4. **Fill the author-owned gaps** (table in section 1). Re-read the paper aloud and keep it in your own words.
5. **Release the code and data pointers.**
   - Add a `LICENSE`. The code imports `pm4py` (AGPL-3.0), so release the code under AGPL-3.0 unless you first replace `pm4py` with your own loader. Put the paper and result tables under CC BY 4.0.
   - Do not publish `realdata/raw` or `realdata/ocel` (git-ignored); point to the source records instead.
   - Search the whole git history for secrets and personal data (`PUBLICATION_CHECKLIST.md` lists this). Remove or keep out the guide-approval screenshot and anything with private addresses.
   - Push to a public GitHub repository, tag `v0.4.0`, and connect it to Zenodo to get a DOI. Put the DOI in `CITATION.cff` (also update its version and release date) and in the paper's Data and code paragraph.
6. **Prepare the files**: manuscript (`Manuscript_v0.4.docx`, plus PDF), figures as separate high-resolution files (`docs/review-3/figures`), the cover letter (`cover_letter.md`), the declarations, and 3 to 5 suggested reviewers with no conflicts (people you do not know personally and who are not co-authors or at VIT; authors of the closest papers are natural candidates, but check each one yourself).
7. **Optional preprint.** Check the journal's policy first. A preprint can carry the same DOI-linked repository. Do not post anything the journal forbids.
8. **Submit** through the journal's online submission system (linked from its page). Create the account, enter the metadata, upload the files, confirm that the work is not under review elsewhere, and submit. Keep the acknowledgement email: it is your proof for the VIT outcome form.
9. **Update VIT's records.** Fill the project-outcome Google form with the submission receipt, and tell your guide.
10. **After submission.** The editor either rejects without review or sends it to reviewers. You will get reviewer comments and a decision (accept, minor or major revision, reject). For a revision, send the revised paper plus a point-by-point response letter, and change the code and results only through `make study`. If it is rejected, read the comments, improve the paper, and try the next venue. Never send it to two venues at the same time.

## 5. Quick commands

```bash
make study                                                           # regenerate every number (about five minutes)
realdata/.venv/bin/python scripts/review3/build_manuscript_docx.py   # rebuild the Word file
python3 -I scripts/review3/make_paper_tables.py                      # print the three tables
```
