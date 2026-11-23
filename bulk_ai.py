"""Reviewable whole-resume improvements with section batches and atomic application."""
from copy import deepcopy
import json
import streamlit as st
from ai_service import (AIError, STYLES, LENGTHS, WritingRequest, improve,
                        NvidiaProvider, validate_suggestion)
from profiles import snapshot, restore

EDITABLE = {
    'personal_info': ('headline', 'summary'),
    'education': ('details',),
    'experience': ('achievements',),
    'skills': ('name', 'category', 'proficiency'),
    'projects': ('title', 'description', 'technologies', 'contributions'),
    'achievements': ('title', 'description'),
    'additional': ('languages', 'extracurricular'),
}


def batches(profile):
    result = {}
    for section, fields in EDITABLE.items():
        entries = {'': profile[section]} if section in ('personal_info', 'additional') else profile[section]
        values = {}
        for entry_id, entry in entries.items():
            for field in fields:
                if entry[field].strip():
                    path = '/'.join(filter(None, (section, entry_id, field)))
                    values[path] = entry[field]
        if values:
            # Bound each request so a large resume cannot exhaust one response's token budget.
            chunk, length, number = {}, 0, 1
            for path, value in values.items():
                new_project = section == 'projects' and chunk and path.rsplit('/', 1)[0] != next(iter(chunk)).rsplit('/', 1)[0]
                if chunk and (new_project or (section != 'projects' and (length + len(value) > 3500 or len(chunk) >= 12))):
                    result[f'{section} {number}'] = chunk
                    chunk, length, number = {}, 0, number + 1
                chunk[path] = value
                length += len(value)
            if chunk:
                result[f'{section} {number}'] = chunk
    return result


def validate_batch(text, original):
    try:
        updated = json.loads(text)
    except (TypeError, ValueError):
        raise AIError('The AI did not return a readable field batch. Original content was kept.') from None
    if not isinstance(updated, dict) or set(updated) != set(original):
        raise AIError('The AI omitted or added fields. Original content was kept.')
    for path, value in updated.items():
        evidence = original[path]
        if path.startswith('projects/'):
            prefix = path.rsplit('/', 1)[0] + '/'
            evidence = '\n'.join(v for k, v in original.items() if k.startswith(prefix))
        validate_suggestion({'text': value, 'questions': []}, evidence)
        if 'basic' in original[path].lower() and not any(term in value.lower() for term in ('basic', 'beginner', 'introductory', 'fundamental')):
            raise AIError('The AI removed a Basic proficiency qualifier. Original content was kept.')
    return updated


def improve_batch(original, section, provider, style='Professional', length='Balanced'):
    result = improve(WritingRequest(json.dumps(original, ensure_ascii=False),
                     'whole-resume batch:' + section, style=style, length=length), consent=True,
                     provider=provider, check=lambda suggestion: validate_batch(suggestion.text, original))
    return json.loads(result.text), result.questions


def apply_review(state):
    review = state.get('bulk_review')
    if not review or snapshot(state) != review['original']:
        return
    updated = deepcopy(review['original'])
    for path, value in review['changes'].items():
        target = updated
        parts = path.split('/')
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
    restore(state, updated)
    state.pop('bulk_review', None)
    state['bulk_message'] = 'Improvements applied across your resume. Preview and exports now use the updated text.'


def bulk_editor(style=None, length=None):
    profile = snapshot(st.session_state)
    provider = NvidiaProvider(model=st.session_state.get('writing_model'))
    groups = batches(profile)
    st.caption('Polish your entire resume in one workflow: summary, education details, every job, skills, project titles/descriptions/contributions, achievements, and languages. Contact details, dates, links, employers, degrees, and official certification names stay as entered.')
    style = style or st.selectbox('Writing style', STYLES, key='bulk_style')
    length = length or st.selectbox('Description length', LENGTHS, index=2, key='bulk_length')
    st.caption(f'{sum(len(v) for v in groups.values())} fields in {len(groups)} batches. Requests may take a few minutes. Only the fields below are sent; no contact details or links are included.')
    with st.expander('Review text that will be sent'):
        st.json(groups)
    st.caption('Improve entire resume sends the displayed fields to NVIDIA NIM, including backup attempts.')
    if not provider.api_key:
        st.info(f'Set {provider.key_variable} to enable AI writing.')
    if st.button('Improve entire resume', type='primary', key='bulk_generate',
                 disabled=not groups or not provider.api_key or st.session_state.get('bulk_busy', False)):
        st.session_state.bulk_busy = True
        # A fresh request replaces previous proposals, never current resume data.
        st.session_state.pop('bulk_review', None)
        changes, errors, questions = {}, [], []
        progress = st.progress(0, text='Preparing resume improvements…')
        try:
            for index, (section, original) in enumerate(groups.items()):
                progress.progress(index / len(groups), text=f'Improving {section}…')
                try:
                    values, followups = improve_batch(original, section, provider, style, length)
                    changes.update({path: value for path, value in values.items() if value != original[path]})
                    questions.extend(followups)
                except AIError as error:
                    errors.append(f'{section}: {error}')
            st.session_state.bulk_review = dict(original=profile, changes=changes, errors=errors,
                                                 questions=questions, destination=provider.models, preferences=(style, length))
            progress.progress(1., text='Review your proposed improvements below.')
        finally:
            st.session_state.bulk_busy = False
    if 'bulk_message' in st.session_state:
        st.success(st.session_state.pop('bulk_message'))
    review = st.session_state.get('bulk_review')
    if review:
        stale = review['original'] != profile or review['destination'] != provider.models
        stale = stale or review.get('preferences', (style, length)) != (style, length)
        if stale:
            st.warning('Your resume or preferred NVIDIA model changed. Generate a fresh review before applying.')
        for error in review['errors']:
            st.warning(error)
        for question in dict.fromkeys(review['questions']):
            st.info(question)
        st.subheader(f"{len(review['changes'])} proposed changes")
        if not review['changes']:
            st.info('No changes were proposed. Review any errors above or try again.')
        original_fields = {k: v for group in batches(review['original']).values() for k, v in group.items()}
        for path, value in review['changes'].items():
            parts = path.split('/')
            entry = review['original'][parts[0]]
            if len(parts) == 3:
                entry = entry[parts[1]]
            title = next((entry.get(k) for k in ('title', 'name', 'job_title', 'institution') if entry.get(k)), '')
            label = ' · '.join(filter(None, [parts[0].replace('_', ' ').title(), title, parts[-1].replace('_', ' ').title()]))
            with st.expander(label):
                before, after = st.columns(2)
                before.caption('Original')
                before.text(original_fields[path])
                after.caption('Improved')
                after.text(value)
        st.button('Apply all improvements', key='bulk_apply', type='primary',
                  disabled=stale or not review['changes'], on_click=apply_review, args=(st.session_state,))
        if st.button('Discard suggestions', key='bulk_discard'):
            st.session_state.pop('bulk_review', None)
            st.rerun()
