# GitHub publication checklist

- [ ] Confirm team names, registration numbers, guide name, and institutional wording.
- [ ] Confirm that the Review 2 presentation may be made public.
- [ ] Remove the guide-approval email screenshot if it contains private email addresses or message content.
- [ ] Confirm that the bundled Educational Capstone Portal architecture documentation is approved for public release.
- [ ] Run `python3 scripts/check_package.py`.
- [ ] Re-run `make study` from a clean `realdata/` setup and confirm that tracked results do not change unexpectedly.
- [ ] Decide the code licence (`pm4py` is AGPL-3.0) and confirm each dataset licence in `realdata/sources.json`.
- [ ] Search the full repository and Git history for secrets and personal data.
- [ ] Choose and add an explicit software/content license; no license has been assumed here.
- [ ] Add the final GitHub repository URL to `CITATION.cff` after creation.
- [ ] Create a tagged Review 2 release and attach the final PPT and report.

