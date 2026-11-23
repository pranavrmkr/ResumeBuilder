"""Resume Builder workspace. Resume content autosaves within this Streamlit session."""
import json
import streamlit as st
from local_config import load_local_env
from exporter import generate_resume_pdf
from preview import resume_markdown
from resume_upload import clear_resume, import_uploaded_resume
from ui import apply_styles, education_form, experience_form, personal_info_form
from profiles import (normalise_profile, initialise, restore, snapshot, checkpoint, travel,
                      duplicate, switch)
from editor_sections import (section_editor, summary_editor, additional_editor, layout_editor)
from analysis_tools import completion
from ai_studio import studio_editor
from resume_styles import RESUME_STYLES

load_local_env()
st.set_page_config(page_title='Resume Builder', page_icon='R', layout='wide')
apply_styles()
initialise(st.session_state)
if 'pending_profile' in st.session_state:
    switch(st.session_state, st.session_state.pop('pending_profile'))


def load_saved_profile(upload_key='json_profile_upload'):
    uploaded_file = st.session_state.get(upload_key)
    if uploaded_file is None:
        return
    try:
        data = normalise_profile(json.loads(uploaded_file.getvalue().decode('utf-8-sig')))
        restore(st.session_state, data)
        st.session_state.json_profile_message = ('success', 'Profile loaded successfully.')
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        st.session_state.json_profile_message = ('error', 'Could not load this file. Please upload a valid Resume Builder JSON profile.')


@st.dialog('Clear this workspace?')
def confirm_clear():
    st.write('This removes all resume profiles, edits, uploads, and history from this session. Download a JSON backup first if you need it.')
    if st.button('Confirm clear', type='primary', key='confirm_clear'):
        clear_resume()
        st.rerun()
    if st.button('Keep editing', key='cancel_clear'):
        st.session_state.pop('show_clear_confirmation', None)
        st.rerun()


st.html('<header class="masthead"><h1>RESUME builder</h1></header>')
st.sidebar.html('<div class="sidebar-brand">Resume Builder</div>')
if st.session_state.get('workspace_step') == 'AI Studio':
    st.session_state.workspace_step = 'AI'
st.session_state.setdefault('workspace_step', 'Edit resume')


def select_step(step):
    st.session_state.workspace_step = step


st.sidebar.button('Edit resume', key='nav_edit', use_container_width=True,
                  type='primary' if st.session_state.workspace_step == 'Edit resume' else 'secondary',
                  on_click=select_step, args=('Edit resume',))
st.session_state.setdefault('editor_section', st.session_state.get('draft_section', 'Personal Info'))
section = st.sidebar.selectbox('Resume section', ('Personal Info', 'Professional Summary', 'Education', 'Experience',
    'Skills', 'Projects', 'Certifications', 'Achievements', 'Additional Information'), key='editor_section',
    on_change=select_step, args=('Edit resume',))
st.session_state.draft_section = section
st.sidebar.button('AI', key='nav_ai', use_container_width=True,
                  type='primary' if st.session_state.workspace_step == 'AI' else 'secondary',
                  on_click=select_step, args=('AI',))
st.sidebar.button('Preview & export', key='nav_preview', use_container_width=True,
                  type='primary' if st.session_state.workspace_step == 'Preview & export' else 'secondary',
                  on_click=select_step, args=('Preview & export',))
workspace = st.session_state.workspace_step
page = section if workspace == 'Edit resume' else workspace
st.session_state.ai_studio_active = workspace == 'AI'
st.html('<div class="workflow-strip">' + ''.join(
    f'<span class="{"current" if workspace == step else ""}">{index}. {step}</span>'
    for index, step in enumerate(('Edit resume', 'AI', 'Preview & export'), 1)) + '</div>')

with st.sidebar.expander('Import & profiles'):
    upload_key = f"resume_upload_{st.session_state.get('upload_version', 0)}"
    st.file_uploader('Resume Upload (PDF or TXT)', type=['pdf', 'txt'], key=upload_key,
                     on_change=import_uploaded_resume, args=(upload_key,))
    st.caption('Recognizes contact details and clearly headed sections. Review imported values. Use JSON for exact restoration.')
    st.file_uploader('Load a saved profile', type=['json'], key='json_profile_upload', on_change=load_saved_profile)
for message in ('upload_message', 'json_profile_message'):
    if message in st.session_state:
        level, text = st.session_state[message]
        getattr(st.sidebar, level)(text)
editor, preview = st.columns([1, 1.2], gap='large')
with editor:
    st.caption({'Edit resume': '01 / BUILD YOUR STORY', 'AI': '02 / REFINE YOUR WRITING', 'Preview & export': '03 / FINISH YOUR RESUME'}[workspace])
    st.subheader(page)
    if page == 'Personal Info':
        personal_info_form()
    elif page == 'Professional Summary':
        summary_editor()
    elif page == 'Education':
        education_form()
    elif page == 'Experience':
        experience_form()
    elif page.lower() in ('skills', 'projects', 'certifications', 'achievements'):
        section_editor(page.lower())
    elif page == 'Additional Information':
        additional_editor()
    elif page == 'AI':
        studio_editor()
    else:
        layout_editor()
        st.info('Review your draft, then generate a PDF below. Empty sections are omitted automatically.')

profile_data = snapshot(st.session_state)
selected_theme = profile_data['settings']['theme']
extra = {key: profile_data[key] for key in ('skills', 'projects', 'certifications', 'achievements', 'additional', 'settings')}
with preview:
    st.caption('LIVE / RESUME PREVIEW')
    st.subheader('Live preview')
    st.caption(profile_data['settings']['template'])
    template_class = RESUME_STYLES[profile_data['settings']['template']]['css']
    # CSS selectors use this local marker; resume text always goes through escaped Markdown.
    theme_class = profile_data['settings']['theme'].lower()
    st.html(f'<div class="template-marker {template_class} theme-{theme_class}"></div>')
    with st.container(border=True, key='resume_sheet'):
        st.markdown(resume_markdown(st.session_state.personal_info, st.session_state.education,
                                    st.session_state.experience, **extra))

checkpoint(st.session_state)
checks = completion(profile_data)
st.sidebar.progress(sum(checks.values()) / len(checks), text=f'Draft essentials · {sum(checks.values())}/{len(checks)}')
st.sidebar.caption('Checks: name, email, summary, skills, education, and experience or projects. Optional sections do not affect this indicator.')
json_data = json.dumps(profile_data, indent=2, ensure_ascii=False)
st.sidebar.download_button('Save Profile (JSON)', json_data, 'resume_profile.json', 'application/json', key='save_profile_json', use_container_width=True)

if st.sidebar.button('Clear Data', key='clear_data'):
    st.session_state.show_clear_confirmation = True
if st.session_state.get('show_clear_confirmation'):
    confirm_clear()

def next_step(step):
    st.session_state.workspace_step = step

st.divider()
if workspace != 'Preview & export':
    destination = 'AI' if workspace == 'Edit resume' else 'Preview & export'
    st.button('Continue to ' + destination, key='continue_workflow', type='primary', on_click=next_step, args=(destination,))
    if workspace == 'Edit resume':
        st.button('Skip AI and preview', key='skip_ai', on_click=next_step, args=('Preview & export',))

if workspace == 'Preview & export':
    st.subheader('Ready for your next step')
    st.caption('Generate a print-ready PDF with the selected template. Review facts, links, and page breaks before sending.')
if workspace == 'Preview & export' and st.button('Generate PDF', type='primary'):
    if not st.session_state.personal_info.get('full_name', '').strip():
        st.warning('Please enter your full name before generating your resume.')
    else:
        try:
            pdf_bytes = generate_resume_pdf(st.session_state.personal_info, st.session_state.education,
                                            st.session_state.experience, **extra)
            st.session_state.generated_pdf = (pdf_bytes, json_data, selected_theme)
            st.success(f'Your resume PDF is ready ({selected_theme}).')
        except (ValueError, OSError) as error:
            st.error(f'PDF generation failed: {error}')
if 'generated_pdf' in st.session_state:
    pdf_bytes, saved_data, saved_theme = st.session_state.generated_pdf
    if (saved_data, saved_theme) == (json_data, selected_theme):
        if workspace == 'Preview & export':
            st.download_button('Download Resume as PDF', pdf_bytes, 'resume.pdf', 'application/pdf', key='download_resume_pdf')
    else:
        st.session_state.pop('generated_pdf', None)
