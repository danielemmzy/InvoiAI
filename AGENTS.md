# Project guidance

## Skill routing

- Before any source-code change, read `docs/PRODUCTION_ROADMAP.md`; use it as the product direction and phase boundary. Re-check the current code before assuming a roadmap item is still missing.

- Use installed skills automatically when their descriptions match the task; do not wait for the user to name or link them.
- For new features, use Superpowers to clarify the approach and plan when the work needs multiple steps. For bugs, use its systematic-debugging workflow.
- Keep implementation focused with Ponytail: prefer the smallest complete change that fits the existing codebase. Karpathy Guidelines overlap with this; apply their shared simplicity and surgical-change principles without repeating the same review.
- For interface work, use UI/UX Pro Max. Add a focused skill such as `animate`, `mobile-native`, or `ask-sonner` only when the task needs it.
- Use VibeWise only after the user explicitly starts `$vibe-wise:learn`; follow its learning checkpoints until they pause or stop that mode.
- For a code review, choose one review workflow that fits the requested scope instead of producing duplicate reports.
- Read and preserve applicable nested `AGENTS.md` instructions. In particular, frontend work must also follow `frontend/AGENTS.md`.
- The user's request and project-specific instructions take precedence over general skill defaults. When skills overlap, use the task-specific skill for its specialty and keep the shared guidance consistent.
- Matt Pocock's engineering skills are installed under `.agents/skills/` (`implement`, `implement-spec`, `to-spec`, `to-tickets`, `code-review`, `diagnosing-bugs`, `tdd`, `triage`, `pr`, `retro`, and others). Prefer them for spec-to-implementation, review, and triage work; the config below tells them where tickets and domain docs live.

## Agent skills

### Issue tracker

Local Markdown only: numbered tickets in `docs/AP_MVP_TICKET_PROPOSAL.md`, direction in `docs/PRODUCTION_ROADMAP.md`, evidence under `docs/database/ticket-*`. No GitHub/Linear tracker. See `docs/agents/issue-tracker.md`.

### Triage labels

No label vocabulary and no tracker labels; ticket state lives in the ticket document. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: roadmap as scope authority, ADRs in `docs/adr/`. See `docs/agents/domain.md`.
