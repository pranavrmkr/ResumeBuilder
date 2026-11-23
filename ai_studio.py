"""One home for writing, summary generation, matching, and provider settings."""
import json
import streamlit as st
from ai_ui import ai_settings, writing_controls
from bulk_ai import bulk_editor, EDITABLE
from editor_sections import summary_editor, analysis_editor
from ai_service import STYLES, LENGTHS, STYLE_GUIDANCE

TOOLS = ['Improve entire resume', 'Professional Summary', 'Rewrite a field', 'Review & Match']


def studio_editor():
    st.caption('Choose a tool, review the source, then accept the suggestions you want. Your original draft stays in place until you apply a change.')
    ai_settings()
    preferences = st.session_state.get('writing_preferences', {})
    st.session_state.setdefault('studio_style', preferences.get('style', 'Professional'))
    st.session_state.setdefault('studio_length', preferences.get('length', 'Balanced'))
    style_col, length_col = st.columns(2)
    style = style_col.selectbox('Writing style', STYLES, key='studio_style')
    length = length_col.selectbox('Description length', LENGTHS, key='studio_length')
    st.session_state.writing_preferences = dict(style=style, length=length)
    st.caption(STYLE_GUIDANCE[style])
    tool = st.selectbox('AI tool', TOOLS, key='studio_tool')
    if tool == 'Improve entire resume':
        bulk_editor(style=style, length=length)
    elif tool == 'Professional Summary':
        summary_editor(assistant=True)
    elif tool == 'Review & Match':
        analysis_editor()
    else:
        rewrite_editor()


def rewrite_editor():
    section = st.selectbox('Resume section', list(EDITABLE), format_func=lambda s: s.replace('_', ' ').title(), key='studio_section')
    if section in ('personal_info', 'additional'):
        data = st.session_state[section]
        entry_id = ''
    else:
        entries = st.session_state[section]
        if not entries:
            st.info('Add an entry in Edit resume first, then return here to refine it.')
            return
        def label(key):
            entry = entries[key]
            title = next((entry.get(f) for f in ('title','name','job_title','institution') if entry.get(f)), 'Untitled entry')
            return f'{list(entries).index(key) + 1}. {title}'
        entry_id = st.selectbox('Entry', list(entries), format_func=label, key='studio_entry_' + section)
        data = entries[entry_id]
    field = st.selectbox('Field to improve', EDITABLE[section], format_func=lambda s: s.replace('_', ' ').title(), key='studio_field_' + section)
    prefix = 'personal' if section == 'personal_info' else section
    key = '_'.join(filter(None, (prefix, entry_id, field)))
    st.session_state.setdefault(key, data[field])
    data[field] = st.text_area('Your text', key=key, height=140)
    context = json.dumps({k: v for k, v in data.items() if k not in ('url', 'start_date', 'end_date')}, ensure_ascii=False) if section == 'projects' else ''
    writing_controls(key, data, field, section, context=context)
