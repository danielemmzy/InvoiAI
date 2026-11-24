# Domain docs

Layout: **single-context**.

## Sources

- `docs/PRODUCTION_ROADMAP.md` — product scope, terminology, confirmed product
  decisions, and phase boundaries. Read it before changing product behaviour.
- `docs/AP_MVP_IMPLEMENTATION_SPEC.md` — reconciled implementation spec.
- `docs/adr/` — architecture decision records. Existing format:
  `Status`, `Date`, `Ticket`, `Context`, `Decision`, `Consequences`, and an
  evidence section when verification is pending.
- No `GLOSSARY.md` exists today. If one is needed, add a single root
  `GLOSSARY.md` and reference it from here; do not introduce per-package
  glossaries.

## Consumer rules

- Use the roadmap's vocabulary (bill, invoice, match, exception, waiver,
  approved-bill write-back, payment instruction) rather than inventing
  synonyms.
- When a decision changes product scope or a provider boundary, write an ADR in
  `docs/adr/` with the ticket number in the header, and link it from the ticket.
- Record only verified provider or database behaviour as fact; mark pending
  evidence explicitly (for example the Sage trial-business evidence).
