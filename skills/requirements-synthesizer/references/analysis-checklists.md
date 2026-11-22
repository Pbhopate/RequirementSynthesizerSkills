# Analysis checklists

Read this during steps 4-6 of the workflow (extract, normalize, find gaps). The checklists exist because
stakeholders talk about what they feel pain about today; they rarely mention the things nobody has
broken yet. A complete specification is one where the silence has been examined, not just the speech.

## Contents
- Where requirements hide in each input type
- Writing a good requirement
- Classifying
- Spotting conflicts
- Gap checklist (non-functional and cross-cutting)
- Prioritization rules
- Common failure modes

## Where requirements hide in each input type

**Meeting transcripts.** Pain points ("we waste hours on..."), workarounds ("we keep a spreadsheet for..."),
modal verbs ("have to", "can't", "need", "ideally", "would be nice"), numbers (volumes, deadlines,
thresholds), names of systems and teams (interfaces, dependencies), disagreement markers ("I don't think",
"but", "that won't work for us"), and commitments or owners ("I'll find out", "legal has to approve").
Attribute every statement to the speaker; two people saying the same thing are two stakeholders on one
requirement, which strengthens it.

**Spreadsheets.** Look at the header row first: it tells you what the sheet is (feature wishlist, bug log,
survey, field mapping, budget). Columns like Priority, Owner, Requested by, Status, Notes carry
stakeholder, priority and caveat data. Free-text "Notes" cells often hold the real constraint. Treat
blank priority as "not stated", not as low. For survey exports, count frequency instead of listing every row.

**Word documents and PDFs.** Existing specs and policies hold business rules and constraints stated as
fact. Tables often contain rules (thresholds, SLAs). Policy documents are sources of constraints, not
wishes. Check for contradictions with what people said in meetings; these are conflicts.

**Emails and slides.** Emails carry decisions and approvals; slides carry the sponsor's framing and
objectives. Both are good for objectives and success metrics.

## Writing a good requirement

1. **One obligation per requirement.** "shall log in and reset passwords" is two. Split on "and" when each
   half could be tested or rejected on its own.
2. **"The system shall <observable behaviour>"** for functional; for non-functional, a measurable quality
   with the number and the conditions ("95th percentile page load under 2 s at 500 concurrent users").
3. **Solution-neutral.** Record the need, not the design. If a stakeholder named a technology, ask whether
   it is a genuine constraint (then put it under constraints) or just their mental picture.
4. **Testable.** If you cannot write an acceptance criterion, it is too vague. Put the missing number
   or definition into an open question and write the criterion as "threshold TBD (Q3)" rather than inventing one.
5. **Never invent facts.** Numbers, names, thresholds and deadlines appear only if a source gave them.
   An invented "99.9% uptime" looks authoritative and will be signed off by someone who assumes it was agreed.
6. **Keep the stakeholder's reason** in `rationale`. It lets a later reader judge trade-offs.

Vague words to replace or quantify: fast, quickly, easy, user-friendly, intuitive, flexible, robust,
scalable, efficient, seamless, minimal, modern, as appropriate, if possible, etc.

## Classifying

| Type | Test | Example |
|---|---|---|
| functional | Describes something the system does | Send a confirmation email on return approval |
| non_functional | A quality of how well it does it | Handles 2,000 returns/day |
| business_rule | A policy that holds regardless of system | Returns accepted within 30 days of delivery |
| data | What must be stored, kept, or migrated | Retain return records 7 years |
| interface | Connection to another system, device or person | Pull orders from the ERP nightly |
| constraint (separate list) | A fixed boundary on solution or project | Must run on the existing Azure tenant |
| assumption (separate list) | Believed true, unverified | Warehouse scanning hardware will not change |

## Spotting conflicts

A conflict exists when satisfying one stakeholder's requirement makes another's impossible or much more
costly. Scan for: same topic with different thresholds (30 vs 60 day window), different priorities for the
same item (Must for Support, Could for Finance), opposing goals (fewer approval steps vs tighter control),
and a source document contradicting what someone said. For each, record every position with its source and
stakeholder. Offer a recommendation only when the sources give grounds for one (objectives, policy,
cost/risk), label it a proposal, and name who must decide. Never quietly pick a winner and drop the other
voice; that is how requirements documents lose trust.

## Gap checklist

For each item, ask: did any source address it? If not and it plausibly matters for this project, raise an
open question (and a derived requirement only when the need is clearly implied). Skip items that are
obviously irrelevant; padding the question list with 30 generic items hides the 5 that matter.

- Roles, permissions, and who approves what
- Performance, volume, peak load, growth horizon
- Availability, maintenance windows, backup and disaster recovery
- Security: authentication, authorization, data classification, encryption, audit trail
- Privacy and compliance: GDPR/CCPA, sector regulation, retention and deletion, consent
- Accessibility (e.g. WCAG level) and supported languages/locales
- Supported browsers, devices, operating systems
- Integrations: systems, direction of data flow, frequency, owners, failure behaviour
- Data: migration from existing systems, quality, reference data ownership, reporting needs
- Reporting and analytics: who needs which metrics, how often
- Notifications and communication preferences
- Error handling, edge cases, exception paths (the unhappy path is usually unspecified)
- Monitoring, support model, training, documentation, rollout and cutover
- Budget, timeline, and team constraints
- Definition of success: how will each objective be measured, and by when

## Prioritization rules

- Use the stakeholder's own words when they gave priority; record `priority_basis: stated`.
- When no one stated it, propose MoSCoW using objective linkage (serves a top objective or legal duty =
  Must; clear benefit but a workaround exists = Should; nice improvement = Could) and record
  `priority_basis: proposed`. Do not present proposed priorities as agreed.
- When stakeholders rate the same item differently, that is a conflict (record it), and the requirement
  carries the highest stated priority with a note.
- Won't = explicitly deferred or excluded this release; use it only when a source said so.

## Common failure modes

- Transcribing the conversation as a list instead of consolidating duplicates into one requirement with several stakeholders.
- Losing the quiet stakeholder: check every stakeholder has at least one requirement or an open question about why not.
- Mixing solution design into requirements.
- Treating a stakeholder's wish as a team decision.
- Burying the gaps: the open-questions section is the most valuable part for the next meeting.
