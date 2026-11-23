"""Review-first writing controls shared by all editable resume sections."""
import json
import streamlit as st
from ai_service import ACTIONS, AIError, NvidiaProvider, WritingRequest, improve, list_nvidia_models


def ai_settings():
    with st.expander('NVIDIA NIM model settings'):
        if st.button('Load NVIDIA models', key='load_nvidia_models'):
            try:
                with st.spinner('Loading model catalog.'):
                    st.session_state.nvidia_models = list_nvidia_models()
            except AIError as error:
                st.error(str(error))
        saved = st.session_state.get('writing_config', {})
        default = NvidiaProvider()
        if 'writing_nvidia_choice' not in st.session_state:
            st.session_state.writing_nvidia_choice = saved.get('nvidia_choice', default.model)
            st.session_state.writing_nvidia_custom = saved.get('nvidia_custom', '')
        custom_option = 'Enter model ID.'
        models = dict.fromkeys([*default.models, *st.session_state.get('nvidia_models', []),
                               st.session_state.writing_nvidia_choice, custom_option])
        selected = st.selectbox('Preferred NVIDIA model', list(models), key='writing_nvidia_choice')
        custom = saved.get('nvidia_custom', '')
        if selected == custom_option:
            st.session_state.setdefault('writing_nvidia_custom', custom)
            custom = st.text_input('Custom NVIDIA model ID', key='writing_nvidia_custom')
        st.session_state.writing_model = custom.strip() if selected == custom_option else selected
        st.session_state.writing_config = dict(nvidia_choice=selected, nvidia_custom=custom)
        st.caption('NVIDIA NIM automatically tries backup models if the preferred model fails. '
                   'Loading the catalog sends no resume text.')


def accept_suggestion(key, data, field):
    suggestion = st.session_state.get('ai_result_' + key)
    if suggestion and suggestion['original'] == data.get(field, ''):
        data[field] = suggestion['text']
        st.session_state[key] = suggestion['text']
        st.session_state.pop('ai_result_' + key, None)


def writing_controls(key, data, field, section, *, summary=False, context=''):
    if not st.session_state.get('ai_studio_active', False):
        return
    with st.expander('Summary assistant' if summary else 'AI Improve', expanded=False):
        provider = NvidiaProvider(model=st.session_state.get('writing_model'))
        if not provider.api_key:
            st.info('Set NVIDIA_API_KEY to enable AI writing. You can keep editing and exporting.')
        action = 'Generate summary' if summary else st.selectbox('Writing action', ACTIONS, key='ai_action_' + key)
        style = st.session_state.get('studio_style', 'Professional')
        length = st.session_state.get('studio_length', 'Balanced')
        original = data.get(field, '')
        source = context if summary else original
        signature = json.dumps(['nvidia', provider.models, source, context, section, action, style, length], ensure_ascii=False)
        st.caption('Text to send')
        st.code(source or '(empty)', language=None)
        if context and not summary:
            st.caption('Context to send')
            st.code(context, language=None)
        st.caption('Generate sends the displayed text and context to NVIDIA NIM, including backup attempts.')
        cached = st.session_state.get('ai_result_' + key)
        busy_key = 'ai_busy_' + key
        if st.button('Regenerate' if cached else 'Generate suggestion', key='ai_generate_' + key,
                     disabled=not provider.api_key or not source.strip() or st.session_state.get(busy_key, False)):
            st.session_state[busy_key] = True
            try:
                with st.spinner('Preparing a suggestion…'):
                    result = improve(WritingRequest(source, section, action, style, length, context if not summary else ''), consent=True, provider=provider)
                st.session_state['ai_result_' + key] = dict(original=original, text=result.text, questions=result.questions,
                                                                 model=provider.last_model, signature=signature)
            except AIError as error:
                st.error(str(error))
            finally:
                st.session_state[busy_key] = False
        result = st.session_state.get('ai_result_' + key)
        if result:
            if result.get('model'):
                st.caption(f"Model used: {result['model']}")
            st.caption('Original')
            st.text(result['original'] or '(empty)')
            st.caption('Suggestion · verify facts before accepting')
            st.text(result['text'])
            for question in result['questions']:
                st.info(question)
            stale = result['original'] != original or result.get('signature') != signature
            if stale:
                st.warning('The source, context, or writing preferences changed. Regenerate before accepting.')
            left, right = st.columns(2)
            left.button('Accept', key='ai_accept_' + key, disabled=stale, on_click=accept_suggestion, args=(key, data, field))
            if right.button('Reject', key='ai_reject_' + key):
                del st.session_state['ai_result_' + key]
                st.rerun()
