# Resume Builder

A Python / Streamlit workspace for building, refining, reviewing, and exporting professional resumes. The app works without an AI key. No database, account, or cloud storage is required.

## Run

Requires Python 3.10 or newer.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed by Streamlit. Start with your contact information, add relevant sections, then use **Preview** to choose a template and **Generate PDF** to prepare a download. Inputs update when you press Enter or leave a field; multiline fields also support Ctrl+Enter.

## What you can build

- Personal information, headline, and professional summary.
- Multiple degrees and jobs, with editable descriptions and one achievement per line.
- Skills with editable custom categories and optional text proficiency. Suggested categories include languages, frameworks, databases, tools, technical and soft skills. Skills display in compact groups without bars or percentages.
- Multiple projects: title, description, technologies, contributions, links, and optional dates. Projects and all new entry sections support moving entries up/down and removing individual entries.
- Certifications with issuer, date, and credential link; achievements with descriptions and optional dates.
- Languages, professional links, portfolio, GitHub, LinkedIn, and extracurricular activities.

The warm light workspace uses serif headings, restrained terracotta accents, refined forms, and an editor beside a live resume sheet. At smaller widths the columns stack. Import and workspace tools are grouped in sidebar disclosures.

## Templates and export

Choose **Preview & export → Resume template**:

1. **Word Template** (default): the supplied two-column Word layout, adapted to profile, skills, contact details, experience, education, projects, and additional resume sections.
2. **Classic Professional**: a single column with traditional serif typography and section rules.
3. **Modern Minimal**: sans-serif typography with restrained accent headings.
4. **Technical Resume**: a compact layout that brings skills and projects forward.
5. **Editorial**: centered serif name, navy headings, and open spacing without section rules.
6. **Compact Professional**: tight sans-serif spacing with the standard section order.

The Word template retains its two-column structure and section order; hide optional sections as needed. Its PDF uses Microsoft Word on Windows to preserve the supplied layout. The other templates use the built-in PDF renderer; **Student / entry-level emphasis** prioritizes education, skills, and projects. Hide optional sections and move sections up/down in those templates. Empty sections stay off the resume.

Choose one of three coordinated color themes: Evergreen, Navy, or Burgundy. Each theme sets resume text, headings and dividers, and the template's tinted panel. The default Word-template export requires Microsoft Word on Windows and the Windows dependency installed from `requirements.txt`.

The browser preview represents resume content and hierarchy; the PDF is the print layout, with its own measured wrapping and pagination. PDF exports support multiple pages, long links, bullet lists, page numbers, clickable email and supported HTTP(S) links, and selectable text colours. A generated download remains available until content, layout, or colour changes.

Noto Sans and Noto Serif fonts are bundled under the SIL Open Font License in `assets/fonts/`; export never downloads fonts at runtime. They support Latin, Greek, and Cyrillic, including accented names and typographic punctuation. These fonts do **not** cover every script or emoji. Unsupported characters produce an explicit error instead of disappearing. CJK, Indic shaping, and RTL typesetting would need additional fonts and shaping configuration.

## Profiles, autosave, and history

Everything autosaves **within the current Streamlit session only**. Navigation preserves edits. Restarting the server, losing the session, or reloading can clear data. Use **Save Profile (JSON)** for a durable local backup.

Version 2 JSON profiles include all sections, template, color theme, visibility, section order, and student mode. Existing version 1 profiles continue loading with empty defaults for new sections. Profile validation completes before replacing current data. Unknown fields are ignored; unsupported future format versions are rejected.

In **Workspace & history**, duplicate a resume under a new name and switch between independent profiles. **Undo / Redo** keeps up to 40 snapshots of content/layout changes in this session. A new edit after Undo clears the redo stack. Imported profiles can also be undone. AI suggestions and PDF bytes are not included in exported JSON or history. Download each named profile separately; JSON contains the selected resume, not the entire workspace. Template and color theme are stored with the resume profile.

**Clear Data** asks for confirmation before clearing the entire session, including all profiles, history, imports, and generated downloads. Individual entry removal is recoverable with Undo.

## Resume import

Upload a PDF with extractable text, or UTF-8 / UTF-16 TXT. Files are read in memory; the app does not save them. Scanned PDFs need a text version (OCR is not included). Review all parsed values before using them.

Recognized headings: Summary / Profile / Professional Summary, Education, Experience / Work Experience / Professional Experience, Skills / Technical Skills, Projects, Certifications, Achievements, and Languages. Contact parsing retains existing fields it cannot recognize. Recognized nonempty sections replace only that section; unparseable sections retain existing entries and report a warning. Re-importing is explicit; normal reruns never overwrite edits.

Education and jobs accept labeled fields, or simple institution/degree and company/role blocks with dates. Separate entries with blank lines. Date ranges such as `2020 - Present` work. An experience entry's `Achievements:` label is retained as job content.

Skills accept comma, pipe, or semicolon-separated names, optionally prefixed by a category. New structured sections use labeled records to avoid guessing facts:

```text
Skills
Programming Languages: Python | SQL
Developer Tools: Git, Docker

Projects
Title: Resume workspace
Description: Built a resume editor.
Technologies: Python, Streamlit
Contributions: Implemented profile imports.
URL: https://example.com/project
Start date: Aug 2024
End date: Present

Certifications
Name: Cloud fundamentals
Issuer: Example Academy
Date: 2024
URL: https://example.com/credential

Achievements
Title: Student showcase
Description: Presented the editor.
Date: 2024

Languages
English, French
```

Freeform new-section paragraphs, multi-column PDFs, and arbitrary professional-link layouts are not reliably reconstructed. Use JSON for exact restoration of every field. Additional Information is edited manually; a Languages heading imports reliably.

## Optional AI writing with NVIDIA NIM

Set your NVIDIA Build key in the terminal that starts Streamlit, then restart the app:

```powershell
$env:NVIDIA_API_KEY = 'your-nvidia-key'
python -m streamlit run app.py
```

The app and `check_nvidia.py` also load `NVIDIA_API_KEY` and optional `NVIDIA_MODEL` from a Git-ignored local `.env` file. Process environment variables take precedence. For deployment, set the key in your host's secrets settings.

Open **AI → NVIDIA NIM model settings** to select a preferred model. By default the app tries Nemotron 3.5 Lightning, then Nemotron 3.5 Bolt if the first model is unavailable, times out, hits a rate limit, or returns an invalid suggestion. You can choose a catalog model or enter a custom ID to try it first. Catalog listing alone does not guarantee account access. Loading the catalog sends no resume text.

Use **AI → Rewrite a field**, then select a section, entry, and field. Expand **AI Improve** to choose an action. Actions: improve wording, make concise, expand, make more technical, make achievement-oriented, fix grammar, convert to bullets, and simplify. Set the shared writing style and length at the top of AI. Tones include Professional, Concise, Technical, Achievement-oriented, ATS-friendly, Confident, Student / Entry-level, Career Change, and Plain English. Length options are Very concise, Short, Balanced (default), and Detailed. These choices persist across tools and navigation; they are writing tones, separate from PDF templates.

**AI → Professional Summary → Summary assistant** generates a summary using existing education, experience, projects, skills, achievements, certifications, and headline. It avoids sending contact details. Change tone/length and regenerate, edit manually, or reject the result.

The app displays the source text and any context before you click Generate. Clicking authorizes the request and any backup attempts through NVIDIA NIM. Attempts use the same input, and additional requests may count toward your account limits. The UI prevents simultaneous submissions and makes no generation calls while typing or navigating. Job-aligned rewriting also sends the displayed job description and current entry.

Original and suggestion are displayed separately. **Accept** applies one suggestion; **Reject** discards it. Changed source text requires regeneration. Prompts prohibit invented facts, and validation rejects empty/malformed responses, unsupported new numeric claims, and added skills from the checked vocabulary. The assistant asks for details when input is vague. No automated validator can guarantee semantic truth: review all experience, outcomes, titles, qualifications, and technical claims before accepting. Length is a generation preference rather than forced word padding.

Missing keys, connectivity errors, API limits, refused/incomplete responses, and invalid output show safe, actionable messages. Editing, matching, quality checks, JSON, and PDFs continue working. Automated tests mock all API calls; no real resume data is sent during testing. A paid live-provider smoke test is deliberately excluded.

## Review & Match

**Quality checker** runs locally. It checks missing name/email/phone, email format, summary and skills, empty entries, inconsistent date formats, descriptions over 100 words, summaries over 90 words, duplicate lines of four or more words, incomplete projects, long unbroken text, hidden skills, and absence of supporting education/experience/projects. Recommendations are actionable; no arbitrary quality score is assigned.

**Job Match Analyzer** runs a separate local keyword comparison against the visible resume. It shows detected keywords, present and unevidenced terms, relevant experience/projects, quality issues, and alignment guidance. Optional AI Improve controls refine relevant entries individually with consent and review.

Coverage is **matched detected keywords / all detected keywords × 100**, rounded to a whole percent. Detection uses a defined technical vocabulary plus repeated meaningful words; matching uses case-insensitive boundaries, including C++/C#. Hidden sections do not count. This estimate is **not an ATS score**, a guarantee, or a semantic assessment of qualifications. Synonyms, negated requirements, and nuanced relevance can be missed. Missing terms are review/learning topics: add a qualification only when you actually possess it.

The sidebar completion indicator checks six draft essentials: name, email, summary, at least one named skill, an education institution, and experience or a project. Optional certifications and achievements never lower completion.

## Validation

```powershell
python -m unittest -v
python -m compileall -q app.py models.py ui.py profiles.py preview.py exporter.py resume_upload.py ai_service.py ai_ui.py analysis_tools.py editor_sections.py
```

The suite covers existing workflows, new entry editing/removal/reordering, session navigation, complete and legacy profiles, atomic invalid imports, named profiles/history, mocked AI success/failure/consent/validation, local analysis, all resume templates, Unicode/link extraction, multi-page wrapping and content bounds, import feedback, and confirmed reset. Two original reset tests now explicitly confirm the destructive action before asserting cleared state.

See `UPGRADE_NOTES.md` for implementation files, validation evidence, and deliberate limits. Generated samples and validation output belong under ignored `samples/` and `output/`, never in commits.

### Restart and clear your draft

To restart, press Ctrl+C in the running Streamlit terminal, then run `python -m streamlit run app.py`. To clear resume data, use **Clear Data → Confirm clear**; this removes all in-session profiles and history. Download a JSON backup first if needed. Neither action resets Git or deletes source changes. Test local AI configuration with `python check_nvidia.py`; it sends only a synthetic test message, and reads `.env` without asking for the key again.

## Improve the entire resume

Uploading a file imports the original text. To polish every writing section, select **AI**, then choose **Improve entire resume** from **AI tool**. Review the text that will be sent, choose a style and description length, and click **Improve entire resume**. This covers the existing summary/headline, education details, every job's bullets, skills/categories/proficiency, project titles/descriptions/technologies/contributions, achievement titles/descriptions, languages, and extracurriculars. Empty fields are skipped rather than invented. Contact information, dates, links, employer/degree names and official certification names are preserved.

The service sends bounded batches and shows progress; a large resume may require several requests and incur provider charges. No calls happen automatically on upload. It validates complete field mappings and checks each proposed value for unsupported numbers and known skills, retaining Basic proficiency qualifiers. Failed batches are reported and their original text remains intact. Review the original/improved comparisons, then click **Apply all improvements** to update all successful suggestions together. **Discard suggestions** keeps your draft. Editing the resume or switching the preferred model makes a pending review stale. Undo can restore the previous draft after applying. All changes flow to the live preview, JSON profiles, and regenerated PDFs.

## Streamlined workflow

1. **Edit resume**: import a resume or JSON profile, choose a section from the section selector, and enter or update your information. AI controls no longer clutter editing forms.
2. **AI**: NVIDIA model settings, shared tone/length controls, whole-resume polishing, summary generation, individual field rewrites, quality checks, and Job Match Analyzer live here. Suggestions always require consent and review. Model and tone/length selections survive navigation.
3. **Preview & export**: choose the supplied Word layout or a built-in style, select a coordinated color theme, hide sections, and generate your PDF. Template and theme choices are included in JSON profiles.

Use the Continue button to move forward, or Skip AI and preview when you prefer manual writing. You can return to any step using the three-item sidebar. The last editing section is remembered. Writing preferences remain separate from resume data and are not exported with candidate profiles. No API request is triggered by navigating between steps.

### Generation controls update

AI tools show a provider disclosure beside their generation buttons. Clicking Generate, Regenerate, or Improve entire resume authorizes that displayed request; there is no separate consent checkbox and no automatic request on upload or navigation. Project rewrites use the actual stack and details of the same project as context. Whole-resume project batches keep each project together and validate against that project rather than rejecting a description for mentioning its own technology stack. Suggestions still require Accept or Apply all improvements.

Sidebar navigation places the resume-section selector immediately below Edit resume and above AI. Choosing a section opens the editor. The Workspace & history panel and its profile/history controls have been removed from the interface; existing in-session data is retained. JSON import/export remains available.
