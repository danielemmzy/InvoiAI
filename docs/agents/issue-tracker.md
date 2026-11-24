# Issue tracker

InvoiAI tracks work in **local Markdown inside this repository**. There is no
GitHub Issues, GitLab, Jira, or Linear tracker for product tickets, and no
`.scratch/` convention. Do not call `gh issue create`, do not create tracker
labels, and do not open or migrate work into an external tracker.

## Where issues live

| Purpose | File |
|---|---|
| Product direction, scope decisions, phase boundaries | `docs/PRODUCTION_ROADMAP.md` |
| Numbered ticket backlog (1–33), dependency table, acceptance criteria | `docs/AP_MVP_TICKET_PROPOSAL.md` |
| Implementation and verification evidence for a ticket | `docs/database/ticket-<n>-<slug>/` (for example `docs/database/ticket-21-22-migration-package/`) |
| Decisions | `docs/adr/NNNN-<slug>.md` |
| Production repair plan and open decisions | `docs/PRODUCTION_REPAIR_PLAN_20261117.md` |

## Conventions to preserve

- Tickets are **numbered sequentially** and referenced as "Ticket 21",
  "Ticket 22". Never renumber, reuse, or reorder existing tickets. New work is
  appended as the next number.
- A ticket in `docs/AP_MVP_TICKET_PROPOSAL.md` uses this shape:

  ```markdown
  ### 21. Purchase orders, goods receipts, and CSV import

  **What it delivers:** ...

  **Blocked by:** 19.

  - [ ] Acceptance criterion
  ```

  Keep the "At a glance" dependency table in sync when tickets are added or
  their blockers change.
- Ticket state lives in the document itself — the proposal's status banner
  (`Proposal only. Not published.`), the `Blocked by` line, and the acceptance
  checkboxes. Do not invent status labels or a separate status file.
- Evidence for completed work is written next to the design docs, not in a
  tracker. Name the folder or file after the ticket number(s).
- Keep `docs/PRODUCTION_ROADMAP.md` as the scope authority. If a request
  conflicts with it, raise the conflict instead of silently changing scope.
- The proposal remains "not published" until the product owner approves the
  ticket split. Do not treat publishing it as a task the engineering skills own.

## How the skills should use this

- **`to-spec` / `to-tickets`**: read the roadmap and the relevant numbered
  ticket, then write or extend the Markdown documents above. Append new tickets
  at the end and update the at-a-glance table; never create a tracker entry.
- **`triage` / `grill-with-docs`**: no labels and no tracker mutations. Report
  priority, blockers, and missing evidence from the ticket text.
- **`implement`**: work from the ticket's acceptance criteria and record
  evidence at the path the ticket names; do not mark a box until the criterion
  is actually verified.
- **Done** means the acceptance checkboxes are checked and the evidence file is
  referenced from the ticket or its evidence folder.
