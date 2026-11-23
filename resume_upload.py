from io import BytesIO
from pathlib import Path
import re
from dataclasses import asdict
from uuid import uuid4

import pdfplumber
import streamlit as st

from models import Education, Experience
from profiles import ENTRY_MODELS


def extract_resume_text(uploaded_file):
    content = uploaded_file.getvalue()
    suffix = Path(uploaded_file.name).suffix.lower()
    try:
        if suffix == ".pdf":
            with pdfplumber.open(BytesIO(content)) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        elif suffix == ".txt":
            encoding = "utf-16" if content.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
            text = content.decode(encoding)
        else:
            raise ValueError("Choose a PDF or TXT file.")
    except UnicodeDecodeError as error:
        raise ValueError("Save your text file as UTF-8 or UTF-16 and try again.") from error
    except ValueError:
        raise
    except Exception as error:
        raise ValueError("Could not read this file. Try another PDF or a text file.") from error
    if not text.strip():
        raise ValueError("No text found. For scanned PDFs, upload a text version instead.")
    return text


def parse_resume_text(text):
    result = {}
    email = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text)
    if email:
        result["email"] = email.group()
    for match in re.finditer(r"(?<!\w)\+?\(?\d[\d ().-]*\d(?!\w)", text):
        phone = match.group().strip()
        if 10 <= len(re.sub(r"\D", "", phone)) <= 15:
            result["phone"] = phone
            break
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    labeled_name = next(
        (re.sub(r"^(?:full\s+)?name\s*:\s*", "", line, flags=re.I)
         for line in lines if re.match(r"^(?:full\s+)?name\s*:", line, re.I)),
        None,
    )
    headings = {"resume", "curriculum vitae", "cv", "personal info", "personal information",
                "contact", "contact info", "contact information", "professional summary",
                "summary", "education", "experience", "work experience", "skills"}
    for line in ([labeled_name] if labeled_name else lines[:8]):
        candidate = re.split(r"[|•]", line)[0].strip()
        words = candidate.split()
        if (candidate.lower() not in headings and 1 <= len(words) <= 5
                and all(any(char.isalpha() for char in word) for word in words)
                and all(char.isalpha() or char in " .'-’" for char in candidate)):
            result["full_name"] = candidate
            break
    return result


def resume_sections(text):
    aliases = {
        "education": "education", "academic qualifications": "education",
        "qualifications": "education", "work experience": "experience",
        "professional experience": "experience", "employment history": "experience",
        "experience": "experience", "summary": "summary",
        "professional summary": "summary", "profile": "summary",
        "skills": "skills", "technical skills": "skills", "projects": "projects",
        "certifications": "certifications", "achievements": "achievements",
        "languages": "languages", "additional information": "additional",
    }
    sections = {"header": []}
    current = "header"
    for line in text.splitlines():
        heading = line.strip().strip("#*: ").lower()
        if heading == 'achievements' and current == 'experience' and line.strip().endswith(':'):
            sections[current].append(line)
        elif heading in aliases:
            current = aliases[heading]
            sections.setdefault(current, [])
        elif heading in {"references", "interests"}:
            current = "other"
            sections.setdefault(current, [])
        else:
            sections[current].append(line)
    return {key: "\n".join(lines).strip() for key, lines in sections.items()}


def parse_entries(text, section):
    defaults = asdict(Education() if section == "education" else Experience())
    aliases = {
        "school": "institution", "university": "institution", "institution": "institution",
        "degree": "degree", "field of study": "field_of_study", "field": "field_of_study",
        "details": "details", "company": "company", "employer": "company",
        "job title": "job_title", "role": "job_title", "title": "job_title",
        "location": "location", "start date": "start_date", "end date": "end_date",
        "achievements": "achievements", "responsibilities": "achievements",
    }
    entries = {}
    date = r"(?:(?:Jan\w*|Feb\w*|Mar\w*|Apr\w*|May|Jun\w*|Jul\w*|Aug\w*|Sep\w*|Oct\w*|Nov\w*|Dec\w*)\s+)?(?:19|20)\d{2}|Present|Current"
    blocks = re.split(r"\n\s*\n", text.strip())
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        entry = defaults.copy()
        remaining = []
        last_field = None
        for line in lines:
            label, separator, value = line.partition(":")
            field = aliases.get(label.lower()) if separator else None
            if field in entry:
                if entry[field] and field in {"institution", "company", "job_title", "degree"}:
                    entries[uuid4().hex] = entry
                    entry = defaults.copy()
                entry[field] = value.strip()
                last_field = field
            elif last_field in {"details", "achievements"}:
                entry[last_field] += "\n" + line.lstrip("-• ")
            else:
                remaining.append(line)
        if not any(entry.values()):
            date_index = next((i for i, line in enumerate(remaining) if re.fullmatch(
                rf"(?:{date})(?:\s*[-–—]\s*(?:{date}))?", line, re.I)), None)
            if date_index is None:
                continue
            before = remaining[:date_index]
            after = remaining[date_index:]
            dates = re.findall(date, after[0], re.I)
            consumed = 1
            if len(dates) == 1 and len(after) > 1 and re.fullmatch(date, after[1], re.I):
                dates.append(after[1])
                consumed = 2
            entry["start_date"] = dates[0]
            entry["end_date"] = dates[1] if len(dates) > 1 else ""
            if section == "education":
                if not before:
                    continue
                degree_first = bool(re.search(r"\b(?:BSc|MSc|BTech|MTech|BA|MA|MBA|PhD|Bachelor|Master|Diploma)\b", before[0], re.I))
                order = ["degree", "institution", "field_of_study"] if degree_first else ["institution", "degree", "field_of_study"]
            else:
                if not before:
                    continue
                role_first = bool(re.search(r"engineer|developer|manager|analyst|intern|designer|consultant", before[0], re.I))
                order = ["job_title", "company", "location"] if role_first else ["company", "job_title", "location"]
            entry.update(dict(zip(order, before)))
            entry["details" if section == "education" else "achievements"] = "\n".join(after[consumed:])
        elif remaining:
            field = "details" if section == "education" else "achievements"
            entry[field] = "\n".join(filter(None, [entry[field], *remaining]))
        entries[uuid4().hex] = entry
    return entries


def parse_new_entries(text, section):
    """Conservative structured import: skills lists, or labeled records for new sections."""
    entries = {}
    if section == 'skills':
        for line in text.splitlines():
            category, sep, names = line.partition(':')
            for name in re.split(r'[,|;]', names if sep else line):
                name = name.strip().lstrip('-• ')
                if name:
                    entries[uuid4().hex] = dict(name=name, category=category.strip() if sep else 'Technical Skills', proficiency='')
        return entries
    aliases = {'project title': 'title', 'certification name': 'name', 'achievement title': 'title',
               'issuing organization': 'issuer', 'technologies used': 'technologies',
               'key contributions': 'contributions', 'project url': 'url', 'credential url': 'url'}
    for block in re.split(r'\n\s*\n', text.strip()):
        entry = asdict(ENTRY_MODELS[section]())
        current = None
        for line in block.splitlines():
            label, separator, value = line.partition(':')
            field = aliases.get(label.strip().lower(), label.strip().lower().replace(' ', '_'))
            if separator and field in entry:
                # Repeated titles begin another record even without a blank line.
                if field in ('title', 'name') and entry[field]:
                    entries[uuid4().hex] = entry
                    entry = asdict(ENTRY_MODELS[section]())
                entry[field] = value.strip()
                current = field
            elif current in ('description', 'contributions'):
                entry[current] += '\n' + line.strip().lstrip('-• ')
        if any(entry.values()) and (entry.get('title') or entry.get('name')):
            entries[uuid4().hex] = entry
    return entries


def import_uploaded_resume(upload_key):
    uploaded_file = st.session_state.get(upload_key)
    st.session_state.pop("upload_message", None)
    if uploaded_file is None:
        return
    try:
        text = extract_resume_text(uploaded_file)
        sections = resume_sections(text)
        parsed = parse_resume_text(sections.get("header", ""))
        imported_sections = {
            section: parse_entries(sections[section], section)
            for section in ("education", "experience") if section in sections
        }
        imported_sections.update({section: parse_new_entries(sections[section], section)
                                 for section in ('skills', 'projects', 'certifications', 'achievements') if section in sections})
        if sections.get("summary"):
            parsed["summary"] = sections["summary"]
    except ValueError as error:
        st.session_state.upload_message = ("error", str(error))
        return
    if not parsed and not any(imported_sections.values()) and not sections.get('languages'):
        st.session_state.upload_message = ("warning", "No resume fields found. Use clear Education and Experience headings.")
        return
    st.session_state.setdefault("personal_info", {}).update(parsed)
    if sections.get('languages'):
        st.session_state.setdefault('additional', {})['languages'] = sections['languages']
        st.session_state['additional_languages'] = sections['languages']
    for field, value in parsed.items():
        st.session_state[f"personal_{field}"] = value
    for section, entries in imported_sections.items():
        if entries:
            for key in list(st.session_state):
                if key.startswith(f"{section}_"):
                    del st.session_state[key]
            st.session_state[section] = entries
    imported = list(parsed) + [f"{len(entries)} {section} entries" for section, entries in imported_sections.items() if entries]
    skipped = [section for section, entries in imported_sections.items() if not entries and sections[section]]
    skipped += [section for section in ('additional',) if sections.get(section)]
    st.session_state.upload_message = (
        "warning" if skipped else "success",
        "Imported " + ", ".join(field.replace("_", " ") for field in imported)
        + ". Please review the forms; layout-based parsing may need corrections."
        + (" Could not parse " + ", ".join(skipped) + "; existing entries were kept. Try labeled fields." if skipped else "")
    )


def clear_resume():
    next_version = st.session_state.get("upload_version", 0) + 1
    st.session_state.clear()
    st.session_state.upload_version = next_version
