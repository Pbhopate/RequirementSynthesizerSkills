---
name: "requirements-synthesizer"
description: Consolidate requirements from multiple stakeholders into one complete, traceable requirements specification delivered as a PDF. Takes meeting transcripts (txt, vtt, srt), spreadsheets (xlsx, xls, csv), Word documents, PDFs, slides and emails as input, extracts and de-duplicates requirements, attributes each to its stakeholders and sources, flags conflicts and gaps, and produces a professional PDF (SRS / BRD style). Make sure to use this skill whenever the user mentions gathering, collecting, consolidating or documenting requirements, a requirements document, BRD, SRS, PRD, stakeholder interviews or workshops, meeting notes or transcripts that need to become requirements, or uploads several stakeholder files and wants a spec, even if they never say "requirements specification".
---

# Requirements Synthesizer

Turn the messy, overlapping, sometimes contradictory things several stakeholders said (in meetings,
spreadsheets and documents) into one specification that a delivery team can build from and a sponsor can
sign off. The finished PDF carries every requirement with its rationale, acceptance criteria, owner,
priority and source citation, and it states plainly what is still unresolved.

The point of the work is trust. A reader should be able to ask "who wanted this, and where did it come
from?" for any line and get an answer, and should see the disagreements and gaps rather than a falsely
tidy document. So: attribute, cite, never invent, and never silently settle a dispute.

## Workflow

Copy this checklist and tick it off as you go.

```
- [ ] 1. Inventory and extract inputs
- [ ] 2. Read everything; register sources and stakeholders
- [ ] 3. Extract candidate requirements with attribution
- [ ] 4. Normalize: split, merge, classify, number
- [ ] 5. Find conflicts, ambiguities and gaps
- [ ] 6. Write requirements.json
- [ ] 7. Validate, build the PDF, inspect it
- [ ] 8. Report back to the user
```

### 1. Inventory and extract inputs

List what the user provided (`/mnt/user-data/uploads`). Then normalize every file to citable text:

```bash
python scripts/extract_inputs.py /mnt/user-data/uploads -o /home/claude/extracted
```

This writes `S1_*.md`, `S2_*.md`, ... plus `manifest.json`, and embeds locators (timestamps, `R14` row
numbers, `[p4]` pages, table rows) so you can cite precisely. Check the printed summary: a source showing
`EMPTY`, `ERROR` or a scanned-PDF warning needs attention (OCR it, or ask the user for a different format)
before you continue, because silently skipping a source means a stakeholder goes unheard.

If the user pasted transcript text into chat instead of uploading, save it to a file first so it gets a
source ID like any other.

### 2. Read everything and register sources and stakeholders

Read each extracted file in full (use `view` with ranges for long ones; for very large spreadsheets sample
the structure, then read the rows that matter and count frequencies for the rest). While reading:

- Create a source entry per file (`S1`...) with type, date if known, and participants.
- Create a stakeholder entry per distinct person or group: name, role, what they care about, how much
  influence they have. Speakers in transcripts, the "Requested by" column in sheets, authors and
  approvers of documents are all stakeholders. If two names are obviously the same person, merge them;
  if unsure, keep separate and add an open question.

If the project name, client, or purpose is not evident, infer it from the sources when it is clear;
otherwise ask the user one short question. Do not block on missing cosmetic metadata (version, author):
default them and move on.

### 3. Extract candidate requirements

Go source by source and pull out every statement of need, rule, constraint, pain point, number, deadline,
integration, and success measure. Use the "where requirements hide" guide in
`references/analysis-checklists.md`. Keep a raw list with speaker/cell and locator for each; consolidating
comes next. Do not filter for importance yet.

### 4. Normalize

- **Split** compound statements so each requirement has one testable obligation.
- **Merge** duplicates and near-duplicates into one requirement that lists all stakeholders and all
  sources. Merging preserves everyone's voice; deleting does not.
- **Rewrite** as "The system shall ..." (functional) or a measurable quality (non-functional), solution-neutral.
- **Classify** as functional, non_functional, business_rule, data, or interface; put fixed boundaries under
  constraints, unverified beliefs under assumptions.
- **Group** with a `category` per area so the PDF reads in sections.
- **Draft acceptance criteria** from what the sources actually said. If a threshold was not given, write
  "threshold TBD (Qn)" and raise the question. Invented numbers are worse than gaps.
- **Prioritize**: use stated priorities; otherwise propose MoSCoW and mark `priority_basis: proposed`.
- **Number** with FR-001, NFR-001, BR-001, DR-001, IR-001.

Details and examples: `references/analysis-checklists.md`.

### 5. Find conflicts, ambiguities and gaps

- **Conflicts**: same topic with different thresholds, priorities, or goals; or a document contradicting
  what someone said. Record every position with stakeholder and source. Propose a resolution only when
  the sources give grounds, label it a proposal, and name the decision owner. Leave status Open.
- **Ambiguities**: vague terms, undefined acronyms, unclear scope boundaries. Add to the glossary if
  resolvable from the sources; otherwise ask.
- **Gaps**: run the gap checklist. For relevant categories no source addressed (security, volumes,
  accessibility, data migration, error handling...), add an open question. Add a requirement only when the
  need is clearly implied, and mark `origin: derived` so reviewers know no one asked for it verbatim.
- **Silent stakeholders**: anyone with no requirements gets an open question.

### 6. Write requirements.json

Follow `references/schema.md` exactly (fields, citation format, ID conventions). Write it to
`/home/claude/requirements.json`. Include an executive `summary` that names the biggest decisions pending,
since that is what a sponsor reads first.

### 7. Validate, build, inspect

```bash
python scripts/validate_requirements.py /home/claude/requirements.json
python scripts/build_requirements_pdf.py /home/claude/requirements.json -o /mnt/user-data/outputs/Requirements_Specification.pdf
```

Fix every error. Treat warnings as a reviewer would: vague wording, missing acceptance criteria, a source
never cited (probably not fully read), a stakeholder with no requirements. Fix or consciously accept.

Then look at the result: rasterize a few pages (`pdftoppm -r 60 -png file.pdf /tmp/pg`) and `view` the
cover, a requirement page, the conflicts page and the traceability page. Check for clipped text, empty
sections, broken characters, and tables overflowing the margins. Rebuild if anything is off. Name the
PDF after the project when the project name is known (e.g. `Returns_Portal_Requirements_v0.1.pdf`).

Deliver with `present_files`.

### 8. Report back

Keep the message short: where the PDF is, how many requirements by type, how many stakeholders and
sources were consolidated, the top 2-3 conflicts needing a decision, and the number of open questions.
State clearly which priorities and derived requirements are proposals. Offer the natural next step:
revise after the stakeholder review, or export the requirements to a spreadsheet for tracking.

## Updating an existing specification

If the user adds new inputs or corrections to a spec made earlier, load the existing `requirements.json`,
keep all existing IDs stable (never renumber; mark retired items instead), add new sources as the next S#,
merge new statements into existing requirements where they overlap, bump `version` and note what changed in
the summary. Rebuild the PDF.

## Principles to keep in mind

- **Attribution is non-negotiable.** Every requirement cites at least one source and one stakeholder.
- **Stated vs. proposed vs. derived** are always distinguishable in the output.
- **Gaps are findings.** An honest open-questions list is more valuable than a polished appearance of completeness.
- **Stakeholder wording matters.** Keep their rationale; keep the number they gave, not a rounder one.
- **Scale the document to the input.** A 20-minute call produces a short spec; do not pad with generic
  boilerplate requirements the sources never implied.
