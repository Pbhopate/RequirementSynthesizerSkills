# requirements.json schema

`scripts/build_requirements_pdf.py` renders this file. Run `scripts/validate_requirements.py` first.
Anything not listed as required may be omitted; the builder skips empty sections.

## Contents
- Top-level shape
- Requirement object
- Citation format
- ID conventions
- Minimal example

## Top-level shape

```json
{
  "meta": {"title": "", "subtitle": "", "project": "", "version": "0.1", "status": "Draft",
           "date": "YYYY-MM-DD", "prepared_by": "", "confidentiality": "Confidential"},
  "summary": "3-6 sentence executive summary: what is being built, for whom, the biggest decisions pending",
  "background": "Why this initiative exists, in the stakeholders' own framing",
  "scope": {"in_scope": ["..."], "out_of_scope": ["..."]},
  "glossary": [{"term": "", "definition": ""}],
  "stakeholders": [{"id": "ST1", "name": "", "role": "", "org": "", "interests": "", "influence": "High|Medium|Low"}],
  "user_roles": [{"name": "", "description": "", "permissions": ""}],
  "objectives": [{"id": "OBJ1", "statement": "", "metric": "", "stakeholders": ["ST1"]}],
  "requirements": [ ...see below... ],
  "assumptions":  [{"id": "A1", "text": "", "source": "S1 @ ..."}],
  "constraints":  [{"id": "C1", "text": "", "source": "S2 @ ..."}],
  "dependencies": [{"id": "D1", "text": "", "owner": ""}],
  "risks": [{"id": "RK1", "description": "", "likelihood": "Low|Medium|High", "impact": "Low|Medium|High", "mitigation": ""}],
  "conflicts": [{"id": "CF1", "topic": "", "requirements": ["FR-004", "FR-009"],
                 "positions": [{"stakeholder": "ST1", "position": "", "source": "S1 @ 00:14:10"}],
                 "impact": "", "recommendation": "", "decision_owner": "", "status": "Open"}],
  "open_questions": [{"id": "Q1", "question": "", "why_it_matters": "", "owner": "", "related": ["FR-004"]}],
  "sources": [{"id": "S1", "name": "original file name", "type": "transcript|spreadsheet|document|pdf|email",
               "date": "", "participants": ""}],
  "next_steps": ["..."]
}
```

## Requirement object

```json
{
  "id": "FR-001",
  "type": "functional | non_functional | business_rule | data | interface",
  "category": "Grouping heading, e.g. 'Returns initiation' or 'Performance'",
  "title": "Short noun phrase",
  "statement": "The system shall ...",
  "rationale": "Why the stakeholder wants it (their reason, not yours)",
  "acceptance_criteria": ["Testable, observable condition", "..."],
  "priority": "Must | Should | Could | Won't",
  "priority_basis": "stated | proposed",
  "stakeholders": ["ST1", "ST3"],
  "objectives": ["OBJ1"],
  "sources": ["S1 @ 00:12:30", "S2 @ Sheet1!R14"],
  "origin": "stated | derived",
  "notes": "Optional caveats, e.g. 'threshold disputed - see CF2'"
}
```

- `origin: derived` means you inferred it (e.g. an audit-trail need implied by a compliance remark). The PDF
  flags these so reviewers know nobody asked for them verbatim.
- `priority_basis: stated` only when a stakeholder actually expressed urgency or optionality.

## Citation format

`"<source id> @ <locator>"`. Locators come from `extract_inputs.py` output:

| Source type | Locator example |
|---|---|
| Transcript with timestamps | `S1 @ 00:12:30` |
| Transcript without timestamps | `S1 @ Priya, "quote of first few words"` |
| Spreadsheet | `S2 @ Sheet1!R14` |
| Word document | `S3 @ §Returns policy` or `S3 @ T-R4` (table row) |
| PDF | `S4 @ p6` |
| Slides | `S5 @ slide 3` |

## ID conventions

FR-### functional, NFR-### non-functional, BR-### business rule, DR-### data, IR-### interface,
ST# stakeholder, OBJ# objective, CF# conflict, Q# open question, A#/C#/D# assumption/constraint/dependency,
RK# risk, S# source. IDs are never reused or renumbered after the user has seen a draft; retire instead.

## Minimal example

```json
{
  "meta": {"title": "Returns Portal Requirements", "version": "0.1"},
  "stakeholders": [{"id": "ST1", "name": "Priya Nair", "role": "Head of Support"}],
  "sources": [{"id": "S1", "name": "kickoff.txt", "type": "transcript"}],
  "requirements": [{
    "id": "FR-001", "type": "functional", "category": "Returns initiation", "title": "Self-service return request",
    "statement": "The system shall let a customer start a return from their order history without contacting support.",
    "acceptance_criteria": ["A logged-in customer can select an eligible order line and submit a return in one session"],
    "priority": "Must", "priority_basis": "stated", "stakeholders": ["ST1"], "sources": ["S1 @ 00:03:12"]
  }]
}
```
