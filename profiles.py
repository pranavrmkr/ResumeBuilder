"""Versioned profiles and bounded in-session history; no disk storage."""
from copy import deepcopy
from dataclasses import asdict
from uuid import uuid4
from resume_styles import RESUME_STYLES
from resume_themes import DEFAULT_RESUME_THEME, RESUME_THEMES

from models import (PersonalInfo, Education, Experience, Skill, Project,
                    Certification, Achievement, AdditionalInfo)

ENTRY_MODELS = dict(education=Education, experience=Experience, skills=Skill,
                    projects=Project, certifications=Certification, achievements=Achievement)
SECTIONS = ['summary', 'education', 'experience', 'skills', 'projects',
            'certifications', 'achievements', 'additional']
TEMPLATES = list(RESUME_STYLES)
DATA_KEYS = ['personal_info', *ENTRY_MODELS, 'additional', 'settings']


def strings(value, model):
    if not isinstance(value, dict):
        raise ValueError('Expected an object for resume fields.')
    defaults = asdict(model())
    if any(isinstance(value.get(k), (dict, list)) for k in defaults):
        raise ValueError('Resume fields must contain text.')
    return {k: str(value.get(k, default) or '') for k, default in defaults.items()}


def normalise_profile(data):
    if not isinstance(data, dict):
        raise ValueError('Invalid JSON structure.')
    if data.get('format_version', 1) not in (1, 2):
        raise ValueError('Unsupported profile version.')
    result = {'format_version': 2, 'personal_info': strings(data.get('personal_info', {}), PersonalInfo)}
    for section, model in ENTRY_MODELS.items():
        entries = data.get(section, {})
        if not isinstance(entries, dict):
            raise ValueError(f'Invalid {section} data.')
        result[section] = {str(key): strings(entry, model) for key, entry in entries.items()}
    result['additional'] = strings(data.get('additional', {}), AdditionalInfo)
    settings = data.get('settings', {})
    if not isinstance(settings, dict):
        raise ValueError('Invalid settings.')
    order = settings.get('section_order', SECTIONS)
    hidden = settings.get('hidden_sections', [])
    if not isinstance(order, list) or not isinstance(hidden, list):
        raise ValueError('Invalid section settings.')
    order = list(dict.fromkeys(s for s in order if s in SECTIONS))
    result['settings'] = {
        'template': settings.get('template') if settings.get('template') in TEMPLATES else TEMPLATES[0],
        'theme': settings.get('theme') if settings.get('theme') in RESUME_THEMES else DEFAULT_RESUME_THEME,
        'section_order': order + [s for s in SECTIONS if s not in order],
        'hidden_sections': [s for s in hidden if s in SECTIONS],
        'student_mode': bool(settings.get('student_mode', False)),
    }
    return result


def snapshot(state):
    return normalise_profile({key: deepcopy(state[key]) for key in DATA_KEYS if key in state})


def initialise(state):
    defaults = normalise_profile({})
    for key in DATA_KEYS:
        state.setdefault(key, deepcopy(defaults[key]))
    state.setdefault('profiles', {})
    state.setdefault('history', [])
    state.setdefault('future', [])
    state.setdefault('active_profile', 'My resume')


def restore(state, data):
    clean = normalise_profile(data)  # Validate everything before mutating any state.
    for key in list(state):
        if key.startswith(('personal_', 'education_', 'experience_', 'skills_', 'projects_',
                           'certifications_', 'achievements_', 'additional_', 'ai_', 'layout_')):
            del state[key]
    for key in DATA_KEYS:
        state[key] = deepcopy(clean[key])
    for field, value in clean['personal_info'].items():
        state[f'personal_{field}'] = value
    state.pop('generated_pdf', None)


def checkpoint(state):
    current = snapshot(state)
    if not state['history'] or state['history'][-1] != current:
        state['history'] = (state['history'] + [current])[-40:]
        state['future'] = []
    state['profiles'][state['active_profile']] = deepcopy(current)


def travel(state, direction):
    if direction == 'undo' and len(state['history']) > 1:
        history = list(state['history'])
        state['future'] = state['future'] + [history.pop()]
        state['history'] = history
        restore(state, history[-1])
    elif direction == 'redo' and state['future']:
        future = list(state['future'])
        target = future.pop()
        state['future'] = future
        state['history'] = state['history'] + [target]
        restore(state, target)


def duplicate(state, name):
    name = name.strip()
    if not name or name in state['profiles']:
        raise ValueError('Choose a new, nonempty profile name.')
    state['profiles'][name] = snapshot(state)
    state['active_profile'] = name


def switch(state, name):
    state['profiles'][state['active_profile']] = snapshot(state)
    restore(state, state['profiles'][name])
    state['active_profile'] = name
    state['history'], state['future'] = [], []


def move_entry(entries, entry_id, offset):
    keys = list(entries)
    index = keys.index(entry_id)
    target = index + offset
    if 0 <= target < len(keys):
        keys[index], keys[target] = keys[target], keys[index]
    return {key: entries[key] for key in keys}


def add_entry(entries, model):
    key = uuid4().hex
    entries[key] = asdict(model())
    return key
