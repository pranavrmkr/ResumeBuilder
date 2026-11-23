# Upgrade implementation and verification

Implemented on `codex/resume-builder-upgrade`, branched from `96c9caf` after fetching `origin/integration/team-features` and confirming its tip (`c24604c`) was already an ancestor. Both requested local commits (`120915b`, `96c9caf`) are preserved. Main was never checked out or modified. No push is performed.

## Implemented features

- Skills CRUD, arbitrary categories, optional text proficiency, compact grouped display.
- Project CRUD and reordering, technical stack, dates, contributions, and links.
- Certifications, achievements, languages, professional links, portfolio, GitHub, LinkedIn, extracurriculars.
- All sections integrated with session editing, complete v2 JSON, legacy v1 loading, live preview, PDF, and conservative text/PDF parsing where reliable.
- Optional NVIDIA NIM writing assistant: eight actions, five styles, four length preferences, context-aware prompts, explicit consent, original/suggestion review, accept/reject/regenerate, safe errors, timeout, in-flight protection, structured output and numeric/known-skill guards.
- Professional summary generation from entered evidence with contact details excluded; manual editing and review before acceptance.
- Local Job Match Analyzer: transparent keyword coverage, present/missing terms, relevant entries, guidance, and optional individual AI wording improvements with job context.
- Separate local quality checker and explicitly defined six-check completion indicator.
- Three templates affect both preview and PDF. Student emphasis, hide sections, custom section order, compact technical layout.
- Bundled licensed Noto fonts, Unicode support beyond Latin-1, clickable links, word wrapping with long-token handling, aligned bullet continuations, heading/entry space reservations, automatic page breaks and footer numbering.
- Session autosave, named profile duplication/switching, bounded undo/redo, complete JSON backups, confirmed Clear Data, conservative import feedback.

## UI and architecture

The original Python/Streamlit architecture, existing dataclasses, personal/education/experience forms, parsing routines, colour themes, and export workflow remain. New modules separate profile lifecycle, AI transport, review controls, local analysis, and additional editors. A semantic block renderer supplies shared content to Markdown and PDF. Warm canvas/sidebar colours, serif display typography, restrained borders and terracotta accents are retained. Desktop uses split editor/preview columns; smaller widths stack them. Sidebar import and history tools sit in disclosures.

The preview is a content/typography guide, not a pixel-perfect paginated PDF viewer. Modern Minimal uses accent headings; Technical Resume reduces spacing and changes emphasis. Existing dependencies remain unchanged; AI transport uses Python's standard library.

## File inventory

Modified:

- `.gitignore`: excludes sample/output/temp directories in addition to existing secrets/caches.
- `README.md`: complete setup, usage, data/privacy, AI configuration, parsing, template, testing, and limitation documentation.
- `app.py`: integrates navigation, editing, profile lifecycle, analysis, preview, exports, and confirmed reset.
- `models.py`: adds dataclasses for skills/projects/certifications/achievements/additional information.
- `ui.py`: preserves original forms and integrates writing review controls.
- `preview.py`: shared semantic resume blocks and escaped Markdown rendering.
- `exporter.py`: Unicode typography, three print templates, pagination, wrapping, bullets, hyperlinks.
- `resume_upload.py`: conservative new-section extraction while preserving legacy import behavior.
- `styles.css`: responsive workspace refinements and template-specific preview styles.
- `test_integration.py`, `test_resume_upload.py`: retain their original workflows and add the explicit confirmation step plus pre-confirmation data-preservation assertions.

Added:

- `profiles.py`: normalized versioned schema, atomic restoration, snapshots, history, named profiles, entry ordering.
- `ai_service.py`: NVIDIA NIM transport, model fallback, factual/output validation and safe exceptions.
- `ai_ui.py`: opt-in writing controls and suggestion review lifecycle.
- `analysis_tools.py`: local keyword, quality, and completion logic.
- `editor_sections.py`: new section editors, summary assistant, template settings and analysis UI.
- `test_upgrade.py`: upgrade regression coverage, including mocked AI calls.
- `assets/fonts/NotoSans-Regular.ttf`, `NotoSans-Bold.ttf`, `NotoSerif-Regular.ttf`, `NotoSerif-Bold.ttf`, `LICENSE.txt`, `README.md`: packaged typography and attribution.
- `UPGRADE_NOTES.md`: this implementation record.

Unchanged: `requirements.txt`, `.streamlit/config.toml`, and `test_app.py`. The existing untracked `PROJECT_AUDIT_REPORT.md` is untouched. Existing `samples/` and `output/` files are retained and excluded from commits.

## Validation

- `python -m unittest -v`: 37 passing tests, including all eight original test workflows (two extended for confirmation).
- `python -m compileall -q ...`: all application modules compile.
- `git diff --check`: no whitespace errors.
- Text and annotation extraction verifies all new sections, accented Latin/Cyrillic text, and clickable links for each template.
- Large synthetic resumes verify multi-page rendering, final-entry preservation, horizontal/vertical content bounds, long unbroken URLs, and section-heading placement across all templates.
- PDF pages are rasterized with pdfplumber's PDFium renderer and visually inspected. All three realistic template examples fit on one page. A long experience sample spans three pages with aligned continuation lines, readable text, reserved margins and page numbers. Generated artifacts are under ignored `output/pdf/`.
- Actual local Streamlit UI exercised in browser: live name/skill editing, custom category, template switching, PDF generation; desktop and small-screen layout inspected.
- Tests use mocked API calls only. No live provider request or API key is required.

## Configuration and running

Install `requirements.txt`, then run `python -m streamlit run app.py`. For optional AI, set `NVIDIA_API_KEY` and optionally `NVIDIA_MODEL` before starting. See the README for setup and fallback behavior.

## Deliberate limits and deferred work

- No cloud/database persistence, authentication, or cross-device sync: scope stays local and session based; download JSON to persist.
- No OCR or inferred parsing of arbitrary new-section paragraphs / complex PDF columns: conservative labeled parsing avoids guessing facts. JSON is exact.
- Keyword matching remains local and heuristic; no claimed ATS score, hiring guarantee, or semantic qualification assessment. Optional AI only rewrites selected evidence.
- No comprehensive semantic fact-checker: numeric and vocabulary guards complement conservative prompts and mandatory human review; they cannot prove truth of every generated sentence.
- No paid live-provider smoke test or real candidate-data transmission during implementation. API transport is tested through mocks.
- Font coverage is Latin/Greek/Cyrillic rather than every Unicode script. CJK, Indic shaping, RTL, and emoji need additional fonts/layout work; unsupported glyphs are reported explicitly.
- No charts/proficiency bars, decorative multi-column resumes, or framework migration: readable single-column output and compatibility take priority.
- Profile JSON exports the selected resume; an entire multi-profile workspace archive and persistent history are deferred to avoid unnecessary storage complexity.

## Workflow and style follow-up (2026-11-14)

The workspace now uses Edit resume → AI Studio → Preview & export. AI provider/model settings, shared style/length preferences, summary generation, targeted rewrites, whole-resume polishing, and job matching live together in AI Studio. Editing forms contain no AI panels. Continue/Skip controls guide the next step; PDF design, colour and downloads are together in the final step. Provider/model and writing preferences survive navigation.

Added Confident, Student / Entry-level, Career Change, and Plain English tones with distinct prompting guidance. Added Editorial and Compact Professional PDF/preview styles. All five styles share definitions in `resume_styles.py`; template choices remain JSON-compatible. New modules include `ai_studio.py`, `test_navigation.py`, and `test_workflow.py`. Existing workflow tests were adapted to the new navigation without removing their assertions. Tests cover no automatic requests, provider/model/tone persistence, apply/undo workflows, all five Unicode PDFs and long-text bounds. Both new styles were rasterized and visually reviewed.
