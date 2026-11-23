import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from test_navigation import navigate,open_summary_rewrite
from ai_service import STYLES,STYLE_GUIDANCE,WritingRequest,NvidiaProvider
from test_nvidia import completion, response


class WorkflowTest(unittest.TestCase):
    def test_guided_steps_and_no_ai_in_forms(self):
        with patch('ai_service.urlopen') as call:
            app=AppTest.from_file('app.py',default_timeout=20).run()
            self.assertEqual([app.sidebar.button(key=k).label for k in ('nav_edit','nav_ai','nav_preview')],['Edit resume','AI','Preview & export'])
            app.text_input(key='personal_full_name').input('Alex').run()
            self.assertFalse(any(e.label in ('AI Improve','Summary assistant') for e in app.expander))
            self.assertFalse(any(b.label=='Generate PDF' for b in app.button))
            app.button(key='continue_workflow').click().run()
            self.assertEqual(app.session_state['workspace_step'],'AI')
            self.assertTrue(app.selectbox(key='writing_nvidia_choice'))
            app.button(key='continue_workflow').click().run()
            self.assertEqual(app.session_state['workspace_step'],'Preview & export')
            self.assertTrue(any(b.label=='Generate PDF' for b in app.button))
            navigate(app,'Personal Info')
            self.assertEqual(app.text_input(key='personal_full_name').value,'Alex')
            self.assertFalse(app.exception)
            call.assert_not_called()

    def test_selected_model_survives_navigation(self):
        app=AppTest.from_file('app.py',default_timeout=20).run()
        open_summary_rewrite(app)
        app.selectbox(key='writing_nvidia_choice').select('Enter model ID.').run()
        app.text_input(key='writing_nvidia_custom').input('example/custom-model').run()
        app.selectbox(key='studio_style').select('Career Change').run()
        app.selectbox(key='studio_length').select('Short').run()
        navigate(app,'Education')
        navigate(app,'Preview')
        open_summary_rewrite(app)
        self.assertEqual(app.selectbox(key='writing_nvidia_choice').value, 'Enter model ID.')
        self.assertEqual(app.text_input(key='writing_nvidia_custom').value,'example/custom-model')
        self.assertEqual(app.selectbox(key='studio_style').value,'Career Change')
        self.assertEqual(app.selectbox(key='studio_length').value,'Short')
        self.assertFalse(app.exception)

    def test_new_styles_roundtrip_in_ui(self):
        app=AppTest.from_file('app.py',default_timeout=20).run()
        navigate(app,'Preview')
        for style in ('Editorial','Compact Professional'):
            app.selectbox(key='layout_template').select(style).run()
            navigate(app,'Skills')
            navigate(app,'Preview')
            self.assertEqual(app.selectbox(key='layout_template').value,style)
            self.assertEqual(app.session_state['settings']['template'],style)
        self.assertFalse(app.exception)

    def test_all_writing_tones_have_distinct_prompt_guidance(self):
        for style in STYLES:
            with patch('ai_service.urlopen', return_value=response(completion())) as call:
                NvidiaProvider(api_key='test').suggest(WritingRequest('Built Python tools.','projects',style=style))
            self.assertIn(STYLE_GUIDANCE[style],call.call_args.args[0].data.decode())
