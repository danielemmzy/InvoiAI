# Document Hub — Open-Source Research

> **Status:** research note. Nothing has been installed, added to `requirements.txt`, or run.
> **Licence rule:** an entry is only marked **verified** if this session read the licence from the
> project's own `LICENSE`, `pyproject.toml`/`package.json` metadata, or PyPI metadata. Anything else is
> marked **unverified** and must not be relied on for a decision.
>
> **"Free" is two different questions.** A permissive licence (free as in FOSS) does not mean zero cost:
> CPU, RAM, image size, storage, egress and maintenance are real. §6 separates the licence question from
> the cost question, and separates both from paid per-document services.

## 1. What has to be produced

| Output | V1 | Source of truth for the content |
|---|---|---|
| PDF (A4, page headers/footers, tables, optional logo) | Yes | Rendered from Jinja2 HTML/CSS |
| XLSX report | Yes | `openpyxl`, existing `ExportService` path |
| CSV report | Yes | Existing `ExportService` path |
| DOCX | Later (Q5[a]) | — |
| Public share links / e-signature / e-invoicing | No (Q5[b],[c],[d]) | — |

Hard constraints from the interview: open-source and self-hostable, no paid per-document APIs, no
external AI in the render path, English only, private storage, short-lived signed downloads.

## 2. Verified candidates

### 2.1 PDF renderers

| Project | Licence (verified) | Evidence | Version / activity seen | Verdict |
|---|---|---|---|---|
| **WeasyPrint** | **BSD-3-Clause** | `Kozea/WeasyPrint/LICENSE` (BSD 3-Clause text), `pyproject.toml` `license = 'BSD-3-Clause'`, PyPI classifier `OSI Approved :: BSD License` | v70 documented on PyPI; ships stable for Python 3.10+; **pin ≥ 70.0** for CVE-2026-55073 (§2.3) | **Recommended primary** |
| **ReportLab** (open-source toolkit) | **BSD** (open-source distribution) | `docs.reportlab.com/developerfaqs` §1.3 "The open-source version of the ReportLab toolkit … available under the BSD license"; PyPI metadata "BSD License (BSD license (see license.txt for details))", classifier `OSI Approved :: BSD License` | v5.x on PyPI | Viable fallback; see licensing trap below |
| **Gotenberg** | **MIT** | `gotenberg/gotenberg/LICENSE` (MIT text), `gotenberg.dev` "Open source under the MIT license" | v9.x, actively released (9.4.1 seen, Nov 2026) | **Recommended fallback** (sidecar) |
| **pypdfium2** | **Apache-2.0 / BSD-3-Clause** (PDFium itself BSD-style) | PyPI licence field `BSD-3-Clause, Apache-2.0, dependency licenses`; project README licensing section | Already pinned in `backend/requirements.txt` at `5.9.0` | Use for page count, merging, thumbnails |

**Licensing traps to record now, not later:**

- ReportLab's *open-source* toolkit is BSD, but ReportLab's commercial products (**ReportLab PLUS /
  RML / rlextra**) are separately licensed and paid. Anything that reaches for `reportlab.rl_config`
  commercial flags, `_renderPM` extras or RML documents is out of bounds. Its docs page also notes the
  commercial product exists to fund the open-source one — read that as "fine, but do not stray into PLUS".
- WeasyPrint's dependencies are the real licence surface: `pydyf`, `tinyhtml5`, `tinycss2`,
  `cssselect2`, `Pyphen`, `Pillow`, `fonttools`, `cffi`. All are permissive as far as the pin set
  already in this repo shows (`cffi`, `pillow` are already dependencies), but the full new transitive
  set must be reviewed at install time. `Pyphen`/`fonttools` bring hyphenation dictionaries and font
  binaries with their own notices.
- Gotenberg bundles **Chromium and LibreOffice** inside the image. The Go wrapper is MIT; the bundled
  components keep their own licences (Chromium: BSD-style plus third-party notices; LibreOffice:
  MPL-2.0). Distributing that image means shipping those notices. This is a real, non-trivial
  compliance difference from an in-process library.

### 2.2 Supporting libraries (already in the dependency set)

`Jinja2` (templating), `openpyxl` (XLSX), `Pillow` (image handling) and `pypdfium2` are already pinned
in `backend/requirements.txt`. Adding no new package for templating and spreadsheet output means no new
licence surface for those layers — which is why the layered recommendation below leans on them.

### 2.3 Security status of the recommended renderer (verified 2026-11-23)

This is a licence research note, but the same primary-source pass found a security fact that changes the
pin and the design, so it is recorded here rather than discovered later.

- **CVE-2026-55073 / GHSA-jf6q-chmf-3h3v** (published 2026-09-08, patched in **70.0**): `url_fetcher` is
  the documented mechanism for blocking `file://` and internal hosts, but two `write_pdf()` channels
  bypassed it by building a fresh default fetcher — `xmp_metadata=[url]` (arbitrary local file read
  embedded verbatim in the PDF) and `stylesheets=[url_or_path]` (SSRF, transitive through the
  `@import`/`url()` graph). Verified from the GitHub advisory and the v70.0 changelog
  ("security update … strongly recommend to upgrade if you embed untrusted images or rely on the URL
  fetcher").
- **GHSA-35jj-wx47-4w8r** (older, patched 61.2): arbitrary files/URLs attachable to a PDF even with a
  restricting fetcher, via `rel=attachment`. Verified from the advisory.

Consequences for the plan (expanded in `ARCHITECTURE_PROPOSAL.md` §9.1): pin `weasyprint>=70.0`; never pass
caller-influenced values to `xmp_metadata=` or `stylesheets=`; build `CSS(string=...)` objects only from
our own stylesheet text; strip `rel=attachment` and other fetching tags from template HTML before render.
A deny-all `url_fetcher` is still required — the advisories show the fetcher is necessary but not
sufficient on its own.

## 3. Evaluated but not recommended for V1

| Option | Why not for V1 | Licence status |
|---|---|---|
| **wkhtmltopdf** | Qt WebKit is effectively frozen; CSS/flex/grid support is poor; separate binary to ship. Wrong direction for a codebase whose UI already assumes modern CSS. | Not re-verified this session (reported GPL/LGPL mix) — treat as needing legal review anyway |
| **Headless Chromium / Playwright in-process** | Adds a ~300 MB browser to the runtime image and a second process model; the roadmap forbids expanding launch surface without evidence. Reach for it only via Gotenberg if WeasyPrint CSS fidelity actually fails. | Not verified (Playwright is Apache-2.0 per its repo; unverified here) |
| **LibreOffice headless directly** | Requires a shot-in-the-dark UNO/CLI wrapper and a large image; only justified for DOCX, which is deferred. | Reported MPL-2.0; not verified this session |
| **Typst** | Excellent engine and fast, but introduces a second template language next to the existing Jinja2 idiom; the team would maintain HTML *and* Typst. | Not verified this session |
| **Carbone / docxtemplater** | Aimed at DOCX/Office templating, deferred with DOCX. | Not verified this session |
| **python-docx** | Clean MIT-licensed DOCX writer — the right pick *when* DOCX is approved. | Not verified this session |
| **docxtpl** | Powerful, but reportedly LGPL-3. A copyleft dependency in the render path is a counsel decision, not an engineering one. | Reported LGPL-3; **unverified** — do not adopt without review |
| **DocRaptor, PDFMonkey, Adobe PDF Services, html2pdf SaaS, DocuSign** | Paid per-document / per-envelope services. Excluded by the stated constraint. | n/a |

## 4. Recommendation

### 4.1 Layered, not monolithic

```
Jinja2 (sandboxed) → HTML + CSS
        ↓
WeasyPrint (in-process)      → typed PDF bytes
        ↓
pypdfium2                    → page count / merge / verify
        ↓
StorageService (existing)    → private object + 300 s signed URL
```

and for tabular reports, reuse the existing Excel path:

```
Snapshot DTO → ExportService → openpyxl XLSX | CSV
```

### 4.2 Why WeasyPrint for V1

- **Licence:** BSD-3-Clause, verified above. Permissive, no copyleft in the render path.
- **Fit:** pure Python, driven by `pip install weasyprint`; the repo already has `cffi` and `Pillow`
  pinned, so the native surface is small and familiar. No sidecar, no Chromium, no port to operate, no
  second failure domain in `docker-compose`.
- **Output shape matches the need:** HTML/CSS with `@page` rules gives real page headers/footers,
  running totals, page-break control and repeated table headers — the things PO/receipt/remittance
  layouts need — and Jinja2 templates are the team's existing idiom.
- **Determinism:** the same HTML/CSS/fonts produce the same PDF, which matters because issued documents
  are frozen and hash-recorded.
- **No AI:** the render path is entirely local. This satisfies "no sensitive document content sent to
  external AI providers by default" without a policy exception.

Known risks, stated honestly:

- WeasyPrint does not implement every modern CSS feature (notably some flex/grid edge cases and
  `position: sticky`-style behaviours). Layouts must be written with print CSS in mind, which is a
  design constraint rather than a defect.
- It is CPU-bound and slower than a warm Chromium; large reports should go to a worker, not a request.
- The Docker image needs the system libraries WeasyPrint's own install docs require (Pango and friends).
  `backend/Dockerfile` was not inspected in this session — **Phase 0 of the roadmap contains the spike
  that must confirm this on the actual image.**

### 4.3 Why Gotenberg stays as the documented fallback

If the spike shows WeasyPrint cannot reach acceptable fidelity (heavy design, complex grid) or throughput
becomes the bottleneck, the drop-in upgrade is a Gotenberg container behind an internal HTTP call:
MIT-licensed software, Chromium/LibreOffice hidden behind an endpoint, keeping the same HTML templates.
That option costs one extra container and a licence-notice obligation, and should only be taken with
evidence — not pre-emptively.

### 4.4 Not adopted at any point in this plan

Paid document APIs (DocRaptor, PDFMonkey, Adobe PDF Services), paid e-signature (DocuSign-class), and
outsourced PDF microservices. Each contradicts the explicit cost constraint and would put customer
financial documents through a third party.

## 5. Licence, infrastructure and paid-service costs are separate questions

No option below charges per generated document. That is the constraint the product owner set, and it is
satisfied by every shortlisted option. What differs is *operational* cost.

| Option | Licence cost | Runtime/infrastructure cost | Hidden cost |
|---|---|---|---|
| **WeasyPrint (primary)** | None. BSD-3-Clause, no fee, no per-document charge | In-process: CPU-bound rendering on existing app/worker capacity; ~1–2 s for a short document (to be measured, not asserted — Phase 0) | Pango/GObject system libraries (LGPL, dynamically linked); image grows modestly; no extra service to operate |
| **Gotenberg (fallback)** | None. MIT, no fee | **Extra container** with bundled Chromium and LibreOffice: meaningful idle RAM, large image, slower cold start, another failure domain and health check | Shipping Chromium/LibreOffice third-party notices; image disk and pull time; container orchestration |
| **ReportLab (toolkit only)** | None. BSD toolkit | Same in-process profile as any pure-Python renderer; different layout paradigm (canvas/platypus, not HTML/CSS) | Commercial PLUS/RML is **paid** — must never be imported; licence audit of the dependency tree |
| **pypdfium2 (already pinned)** | None | Negligible (page count/merge only) | None found |
| **Jinja2 / openpyxl / CSV (already pinned)** | None | Negligible for templating and tabular export | None added |
| **Object storage for generated PDFs** | Not a software licence — it is the existing Supabase storage product | Per-GB storage and egress billed by the hosting provider; retention policy directly changes the bill | **Not free** and outside this document's control; the estimate belongs to the hosting plan, not the licence table |
| **Paid per-document APIs** (DocRaptor, PDFMonkey, Adobe PDF Services, html2pdf SaaS) | Commercial | Vendor-hosted, per-document pricing | Excluded by the product constraint, and they would send customer financial documents to a third party |
| **Paid e-signature** (DocuSign-class) | Commercial | Per-envelope pricing | Excluded: e-signature is out of V1 entirely |

Reading of the constraint: "open-source and self-hostable, no paid per-document generation APIs" is met
by WeasyPrint and Gotenberg. It is **not** met by any SaaS generator, and it does not promise that
infrastructure is free — storage and compute are still billed by whoever hosts them.

## 6. Licence and maintenance items to re-check at install time

| Item | Check |
|---|---|
| Full transitive tree of the PDF path | `pip install --dry-run` and review every new package + its licence |
| Fonts bundled for the letterhead | Font file licences (OFL vs proprietary) must permit embedding and redistribution |
| WeasyPrint system libraries | Pango/cairo GObject stack is LGPL — acceptable as dynamically linked system libs, but record it |
| Gotenberg image, if adopted | Chromium/LibreOffice notices shipped with the deployment |
| ReportLab, if adopted | Confirm only BSD-covered modules are used; no plus/rml imports |
| python-docx, when DOCX is approved | Verify MIT and no bundled Office dependency |
| Every candidate | Last release date and open security advisories at the moment of adoption |
| WeasyPrint | Confirm resolved version is **≥ 70.0**; re-read the security advisories page before each upgrade |
| fonts | Confirm the chosen font may be embedded and redistributed; record its OFL/proprietary status |

## 7. Sources read this session

- `github.com/Kozea/WeasyPrint` — `LICENSE`, `README.rst`, `pyproject.toml`
- `pypi.org/project/weasyprint/`, `doc.courtbouillon.org/weasyprint/stable/`
- `docs.reportlab.com/developerfaqs` (§1.3 Licensing), `pypi.org/project/reportlab`
- `github.com/gotenberg/gotenberg` — `LICENSE`, README; `gotenberg.dev`
- `pypi.org/project/pypdfium2`, `github.com/pypdfium2-team/pypdfium2` licensing section
- `github.com/advisories/GHSA-jf6q-chmf-3h3v` (CVE-2026-55073), `osv.dev/PYSEC-2026-3940`,
  `github.com/Kozea/WeasyPrint/security/advisories/GHSA-35jj-wx47-4w8r`
- `doc.courtbouillon.org/weasyprint/stable/first_steps.html` (Security, URL Fetchers, Attachments),
  `.../stable/api_reference.html` (`URLFetcher`, `DEFAULT_OPTIONS`), `.../stable/changelog.html` (v70.0)
