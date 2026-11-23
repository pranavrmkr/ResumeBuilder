"""Shared semantic resume content for Markdown preview and PDF export."""
import re
from dataclasses import dataclass
from urllib.parse import urlparse
from profiles import normalise_profile


@dataclass
class Block:
    kind: str
    text: str
    link: str = ''


def safe_link(value):
    value = value.strip()
    return value if urlparse(value).scheme.lower() in ('https', 'http', 'mailto') else ''


def plain_text(value):
    return re.sub(r'([\\`*_{}\[\]()#+\-.!|>~])', r'\\\1', value.strip())


def resume_blocks(profile):
    p = normalise_profile(profile)
    info, settings = p['personal_info'], p['settings']
    blocks = [Block('name', info['full_name'] or 'Your name')]
    if info['headline']:
        blocks.append(Block('headline', info['headline']))
    contact = [info[k] for k in ('email', 'phone', 'location', 'website') if info[k]]
    if contact:
        blocks.append(Block('contact', ' · '.join(contact)))
    # Separate link annotations keep contact text compact in both renderers.
    def line(kind, text, link=''):
        if text.strip():
            blocks.append(Block(kind, text.strip(), safe_link(link)))
    order = list(settings['section_order'])
    if settings['template'] == 'Word Template':
        order = ['summary', 'skills', 'experience', 'education', 'projects',
                 'certifications', 'achievements', 'additional']
    if settings['template'] == 'Technical Resume':
        order = ['summary', 'skills', 'projects'] + [s for s in order if s not in ('summary', 'skills', 'projects')]
    if settings['student_mode']:
        order = ['summary', 'education', 'skills', 'projects'] + [s for s in order if s not in ('summary', 'education', 'skills', 'projects')]
    titles = dict(summary='Profile', education='Education', experience='Experience', skills='Skills', projects='Projects',
                  certifications='Certifications', achievements='Achievements', additional='Additional Information')
    for section in order:
        if section in settings['hidden_sections']:
            continue
        start = len(blocks)
        if section == 'summary':
            line('body', info['summary'])
        elif section == 'skills':
            groups = {}
            for skill in p['skills'].values():
                if skill['name'].strip():
                    groups.setdefault(skill['category'] or 'Skills', []).append(skill['name'] + (f" ({skill['proficiency']})" if skill['proficiency'] else ''))
            for category, names in groups.items():
                line('skill', category + ': ' + ' | '.join(names))
        elif section == 'additional':
            for field, value in p['additional'].items():
                if value:
                    for index, item in enumerate(value.splitlines()):
                        label = field.replace('_', ' ').title() + ': ' if index == 0 else ''
                        line('body', label + item, item)
        else:
            for entry in p[section].values():
                if not any(v.strip() for v in entry.values()):
                    continue
                if section == 'education':
                    line('entry', ' — '.join(filter(None, [entry['degree'], entry['field_of_study']])) or 'Degree')
                    line('body', entry['institution'])
                    detail = entry['details']
                elif section == 'experience':
                    line('entry', entry['job_title'] or 'Job title')
                    line('body', ' · '.join(filter(None, [entry['company'], entry['location']])))
                    detail = entry['achievements']
                elif section == 'projects':
                    line('entry', entry['title'] or 'Project')
                    line('body', entry['technologies'])
                    line('body', entry['description'])
                    line('body', entry['url'], entry['url'])
                    detail = entry['contributions']
                elif section == 'certifications':
                    line('entry', entry['name'] or 'Certification')
                    line('body', entry['issuer'])
                    line('body', entry['url'], entry['url'])
                    detail = ''
                else:
                    line('entry', entry['title'] or 'Achievement')
                    detail = entry['description']
                line('date', ' – '.join(filter(None, [entry.get('start_date', entry.get('date', '')), entry.get('end_date', '')])))
                for item in detail.splitlines():
                    line('bullet' if section in ('experience', 'projects') else 'body', re.sub(r'^[-*•]\s*', '', item.strip()))
        if len(blocks) > start:
            blocks.insert(start, Block('section', titles[section]))
    return blocks


def resume_markdown(personal_info, education, experience, **extra):
    blocks = resume_blocks(dict(personal_info=personal_info, education=education, experience=experience, **extra))
    lines = []
    previous_kind = None
    for block in blocks:
        text = plain_text(block.text)
        if block.kind == 'skill':
            category, _, names = block.text.partition(': ')
            text = f'**{plain_text(category)}:** {plain_text(names)}'
        if block.link:
            text = f'[{text}]({block.link.replace(")", "%29").replace("(", "%28")})'
        prefix = {'name': '# ', 'section': '## ', 'entry': '### ', 'bullet': '- '}.get(block.kind, '')
        # Consecutive bullets must share a Markdown list, not separate paragraphs.
        separator = '\n' if block.kind == 'bullet' and previous_kind == 'bullet' else '\n\n'
        if lines:
            lines.append(separator + prefix + text)
        else:
            lines.append(prefix + text)
        previous_kind = block.kind
    return ''.join(lines)
