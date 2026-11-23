"""Transparent, local keyword matching and resume quality checks. No remote calls."""
from collections import Counter
import re
from preview import resume_blocks

SKILL_TERMS = ['Python', 'C++', 'C#', 'Java', 'JavaScript', 'TypeScript', 'SQL', 'HTML', 'CSS',
               'React', 'Node.js', 'Flask', 'Django', 'Streamlit', 'Git', 'GitHub', 'Docker',
               'Kubernetes', 'AWS', 'Azure', 'GCP', 'PostgreSQL', 'MySQL', 'MongoDB', 'Linux',
               'REST', 'API', 'APIs', 'Machine Learning', 'Data Analysis', 'Excel', 'Figma',
               'Communication', 'Leadership', 'Testing', 'CI/CD', 'Agile', 'Project Management']
STOP = set('the a an and or to of in for with on is are be as by we you our your will have has this that from at work role team must required requirements experience skills strong ability using knowledge years responsibilities job candidate looking seeking preferred including'.split())


def contains(text, term):
    return bool(re.search(r'(?<![\w+#])' + re.escape(term) + r'(?![\w+#])', text, re.I))


def keywords(text):
    known = [term for term in SKILL_TERMS if contains(text, term)]
    counts = Counter(w.lower() for w in re.findall(r'[a-zA-Z][a-zA-Z-]{2,}', text) if w.lower() not in STOP)
    extras = [w for w, count in counts.most_common(30) if count >= 2 and w not in {s.lower() for s in known}]
    return known + extras[:15]


def analyze_job(profile, description):
    terms = keywords(description)
    resume = '\n'.join(b.text for b in resume_blocks(profile) if b.kind != 'name')
    present = [term for term in terms if contains(resume, term)]
    missing = [term for term in terms if term not in present]
    relevant = []
    for section in ('experience', 'projects'):
        if section in profile.get('settings', {}).get('hidden_sections', []):
            continue
        for key, entry in profile.get(section, {}).items():
            matched = [term for term in terms if contains(' '.join(entry.values()), term)]
            if matched:
                relevant.append({'section': section, 'id': key, 'title': entry.get('title') or entry.get('job_title') or 'Untitled', 'keywords': matched})
    return {'keywords': terms, 'present': present, 'missing': missing,
            'coverage': round(100 * len(present) / len(terms)) if terms else None,
            'relevant': relevant,
            'suggestions': ['Clarify relevant contributions in the entries listed below using only your actual work.',
                            'For missing terms, add evidence only if you already have that qualification; otherwise treat it as a learning topic.']}


def quality_check(profile):
    issues = []
    info = profile.get('personal_info', {})
    for field in ('full_name', 'email', 'phone'):
        if not info.get(field, '').strip():
            issues.append(f'Add your {field.replace("_", " ")} to contact information.')
    if info.get('email') and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', info['email']):
        issues.append('Check the email address format.')
    if not info.get('summary', '').strip():
        issues.append('Add a brief professional summary based on your actual background.')
    if not any(s.get('name', '').strip() for s in profile.get('skills', {}).values()):
        issues.append('Add relevant skills you can demonstrate.')
    dates, phrases = set(), []
    for section in ('education', 'experience', 'skills', 'projects', 'certifications', 'achievements'):
        for entry in profile.get(section, {}).values():
            # A category alone does not make an empty skill useful.
            content = [v for k, v in entry.items() if k not in ('category', 'proficiency')]
            if not any(v.strip() for v in content):
                issues.append(f'Remove or complete an empty {section} entry.')
            if section == 'projects' and (not entry.get('title') or not entry.get('description') or not entry.get('technologies')):
                issues.append('Complete each project title, description, and technologies.')
            for field, value in entry.items():
                if 'date' in field or field == 'date':
                    if value and value.lower() not in ('present', 'current'):
                        kind = ('year' if re.fullmatch(r'\d{4}', value) else 'month-year' if re.fullmatch(r'[A-Za-z]+ \d{4}', value) else 'iso' if re.fullmatch(r'\d{4}-\d{2}(?:-\d{2})?', value) else 'other')
                        dates.add(kind)
                if field in ('description', 'contributions', 'details', 'achievements'):
                    if len(value.split()) > 100:
                        issues.append(f'Shorten a long {section} description (over 100 words).')
                    phrases += [s.strip().lower() for s in value.splitlines() if len(s.strip().split()) >= 4]
    if len(dates) > 1 or 'other' in dates:
        issues.append('Use consistent dates, such as Aug 2024 or Present, across entries.')
    if any(count > 1 for count in Counter(phrases).values()):
        issues.append('Replace repeated lines with distinct, specific contributions.')
    if len(info.get('summary', '').split()) > 90:
        issues.append('Shorten the summary to focus on your most relevant qualifications.')
    if any(len(word) > 70 for b in resume_blocks(profile) for word in b.text.split()):
        issues.append('Review very long links or unbroken text for print readability.')
    hidden = profile.get('settings', {}).get('hidden_sections', [])
    if 'skills' in hidden and profile.get('skills'):
        issues.append('Your skills are hidden from export. Show them when relevant to the role.')
    if not profile.get('education') and not profile.get('experience') and not profile.get('projects'):
        issues.append('Add education, experience, or projects to support your qualifications.')
    return list(dict.fromkeys(issues))


def completion(profile):
    """Six explicit checks; optional certifications and achievements do not affect completion."""
    p = profile.get('personal_info', {})
    checks = {'Name': bool(p.get('full_name', '').strip()), 'Email': bool(p.get('email', '').strip()),
              'Summary': bool(p.get('summary', '').strip()),
              'Skills': any(s.get('name', '').strip() for s in profile.get('skills', {}).values()),
              'Education': any(e.get('institution', '').strip() for e in profile.get('education', {}).values()),
              'Experience or projects': any(any(v.strip() for v in e.values()) for s in ('experience', 'projects') for e in profile.get(s, {}).values())}
    return checks
