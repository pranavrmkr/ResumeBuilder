"""Editors for additional sections and local analysis tools."""
import json
import streamlit as st
from dataclasses import asdict
from models import AdditionalInfo
from profiles import ENTRY_MODELS, add_entry, move_entry, snapshot, SECTIONS, TEMPLATES
from analysis_tools import analyze_job, quality_check
from ai_ui import writing_controls
from resume_styles import STYLE_DESCRIPTIONS
from resume_themes import RESUME_THEMES

LABELS = {
    'skills': {'name': 'Skill', 'category': 'Category (custom categories welcome)', 'proficiency': 'Proficiency (optional)'},
    'projects': {'title': 'Project title', 'description': 'Description', 'technologies': 'Technologies used',
                 'contributions': 'Key contributions (one per line)', 'url': 'Project or GitHub URL', 'start_date': 'Start date (optional)', 'end_date': 'End date (optional)'},
    'certifications': {'name': 'Certification name', 'issuer': 'Issuing organization', 'date': 'Date', 'url': 'Credential URL'},
    'achievements': {'title': 'Achievement title', 'description': 'Description', 'date': 'Date (optional)'},
}


def section_editor(section):
    entries = st.session_state[section]
    singular = dict(skills='skill', projects='project', certifications='certification', achievements='achievement')[section]
    if section == 'skills':
        st.caption('Suggested categories: Programming Languages · Frameworks and Libraries · Databases · Developer Tools · Technical Skills · Soft Skills · Other. Type any custom category. Proficiency is optional.')
    if st.button('Add ' + singular, type='primary'):
        add_entry(entries, ENTRY_MODELS[section])
        st.rerun()
    if not entries:
        st.info(f'Add a {singular} when it is relevant to your next role. Empty sections stay off your resume.')
    for entry_id, data in list(entries.items()):
        with st.container(border=True):
            st.markdown(f'**{singular.title()} {list(entries).index(entry_id) + 1}**')
            for field, label in LABELS[section].items():
                key = f'{section}_{entry_id}_{field}'
                st.session_state.setdefault(key, data[field])
                widget = st.text_area if field in ('description', 'contributions') else st.text_input
                data[field] = widget(label, key=key)
            actions = st.columns(3)
            if actions[0].button('Remove ' + singular, key=f'remove_{section}_{entry_id}'):
                del entries[entry_id]
                st.rerun()
            for col, label, offset in ((actions[1], 'Move up', -1), (actions[2], 'Move down', 1)):
                index = list(entries).index(entry_id)
                if col.button(label, key=f'{section}_{entry_id}_move{offset}', disabled=not 0 <= index + offset < len(entries)):
                    st.session_state[section] = move_entry(entries, entry_id, offset)
                    st.rerun()


def summary_editor(assistant=False):
    info = st.session_state.personal_info
    key = 'personal_summary'
    st.session_state.setdefault(key, info['summary'])
    info['summary'] = st.text_area('Professional summary', key=key, height=160)
    profile = snapshot(st.session_state)
    # Keep contact information out of the summary request.
    evidence = {s: {k: entry for k, entry in profile[s].items()
                    if any(v.strip() for field, v in entry.items() if field not in ('category', 'proficiency'))}
                for s in ENTRY_MODELS}
    evidence['headline'] = profile['personal_info']['headline']
    evidence['summary'] = info['summary']
    if assistant:
        writing_controls(key, info, 'summary', 'professional summary', summary=True,
                         context=json.dumps(evidence, ensure_ascii=False, indent=2) if any(evidence.values()) else '')


def additional_editor():
    data = st.session_state.additional
    for field in asdict(AdditionalInfo()):
        key = 'additional_' + field
        st.session_state.setdefault(key, data[field])
        widget = st.text_area if field in ('languages', 'professional_links', 'extracurricular') else st.text_input
        data[field] = widget(field.replace('_', ' ').title(), key=key)


def layout_editor():
    settings = st.session_state.settings
    st.caption('Choose how your resume reads on screen and in print.')
    settings['template'] = st.selectbox('Resume template', TEMPLATES, index=TEMPLATES.index(settings['template']), key='layout_template')
    st.caption(STYLE_DESCRIPTIONS[settings['template']])
    settings['theme'] = st.selectbox('Resume color theme', list(RESUME_THEMES),
                                     index=list(RESUME_THEMES).index(settings['theme']), key='layout_color_theme')
    colors = RESUME_THEMES[settings['theme']]
    if settings['template'] == 'Word Template':
        st.caption(f"Text #{colors['text']} · Accent and dividers #{colors['accent']} · Panel #{colors['surface']}")
    else:
        st.caption(f"Text #{colors['text']} · Accent #{colors['accent']}")
    if settings['template'] == 'Word Template':
        st.caption('The Word template keeps its designed section order. You can hide sections above.')
    else:
        settings['student_mode'] = st.checkbox('Student / entry-level emphasis', value=settings['student_mode'], key='layout_student')
    settings['hidden_sections'] = st.multiselect('Hide optional sections', SECTIONS, default=settings['hidden_sections'], key='layout_hidden')
    if settings['template'] != 'Word Template':
        with st.expander('Section order'):
            order = settings['section_order']
            st.caption('Technical and student templates prioritize their key sections; custom order applies to the remaining sections.')
            for index, section in enumerate(order):
                cols = st.columns([3, 1, 1])
                cols[0].write(section.replace('_', ' ').title())
                for col, label, offset in ((cols[1], '↑', -1), (cols[2], '↓', 1)):
                    if col.button(label, key=f'layout_order_{section}_{offset}', disabled=not 0 <= index + offset < len(order)):
                        order[index], order[index + offset] = order[index + offset], order[index]
                        st.rerun()


def analysis_editor():
    profile = snapshot(st.session_state)
    quality, match = st.tabs(['Quality checker', 'Job Match Analyzer'])
    with quality:
        st.caption('Local checks · no AI or data transmission · no arbitrary score')
        issues = quality_check(profile)
        if not issues:
            st.success('No issues found by the local checks. Review your content and print layout before sending.')
        for issue in issues:
            st.warning(issue)
    with match:
        st.caption('Local keyword comparison. Coverage = matched keywords ÷ detected keywords. This is an estimate, not an ATS score or a hiring prediction.')
        description = st.text_area('Job description', key='job_description', height=200, max_chars=40000)
        if st.button('Analyze job description', disabled=not description.strip()):
            st.session_state.job_analysis = (description, profile, analyze_job(profile, description))
        saved = st.session_state.get('job_analysis')
        if saved:
            if saved[:2] != (description, profile):
                st.info('Resume or job description changed. Analyze again for current results.')
                return
            result = saved[2]
            st.metric('Estimated keyword coverage', f"{result['coverage']}%" if result['coverage'] is not None else 'No keywords detected')
            st.caption('Detected from a defined technical vocabulary plus repeated nontrivial words; synonyms and context may be missed.')
            st.write('Important keywords: ' + (', '.join(result['keywords']) or 'None detected'))
            st.success('Present in visible resume: ' + (', '.join(result['present']) or 'None detected'))
            st.warning('Not evidenced in visible resume: ' + (', '.join(result['missing']) or 'None detected'))
            for suggestion in result['suggestions']:
                st.write(suggestion)
            for issue in quality_check(profile):
                st.caption(issue)
            for item in result['relevant']:
                st.markdown(f"**{item['title']}** · {', '.join(item['keywords'])}")
                entry = st.session_state[item['section']][item['id']]
                field = 'achievements' if item['section'] == 'experience' else 'description'
                key = f"{item['section']}_{item['id']}_{field}"
                writing_controls(key, entry, field, item['section'], context=json.dumps({'existing_entry': entry, 'job_description': description}, ensure_ascii=False))
