from io import BytesIO
from test_navigation import navigate
import json
import unittest

import pdfplumber
from streamlit.testing.v1 import AppTest

from exporter import generate_resume_pdf


class IntegrationTest(unittest.TestCase):
    def test_profiles_and_download(self):
        app = AppTest.from_string(
            "from pathlib import Path\n"
            "exec(Path('app.py').read_text(encoding='utf-8'))\n"
            "st.session_state['saved_json'] = json_data\n"
            "st.button('Load test profile', key='load_test', on_click=load_saved_profile, args=('incoming',))\n"
        ).run()
        app.text_input(key="personal_full_name").input("Latest Name").run()
        self.assertEqual(json.loads(app.session_state['saved_json'])['personal_info']['full_name'], 'Latest Name')
        profile = {'format_version': 1, 'personal_info': {'full_name': 'Alex Smith'},
                   'education': {'a': {'degree': 'BSc', 'institution': 'Example University'}},
                   'experience': {'b': {'job_title': 'Developer', 'company': 'Example Co'}}}
        upload = BytesIO(json.dumps(profile).encode())
        app.session_state['incoming'] = upload
        app.button(key='load_test').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text_input(key='personal_full_name').value, 'Alex Smith')
        self.assertIn('Example University', app.markdown[-1].value)
        navigate(app, 'Preview')
        next(button for button in app.button if button.label == 'Generate PDF').click().run()
        self.assertFalse(app.exception)
        self.assertIn('generated_pdf', app.session_state)
        data = app.session_state['generated_pdf'][0]
        with pdfplumber.open(BytesIO(data)) as pdf:
            text = '\n'.join(page.extract_text() for page in pdf.pages)
        for expected in ('Alex Smith', 'Example University', 'Developer', 'Example Co'):
            self.assertIn(expected, text)
        app.run()
        self.assertTrue(any(button.key == 'download_resume_pdf' for button in app.get('download_button')))
        app.selectbox(key='pdf_font_theme').select('Forest Green').run()
        self.assertNotIn('generated_pdf', app.session_state)
        navigate(app, 'Personal Info')
        app.session_state['incoming'] = BytesIO(b'not json')
        app.button(key='load_test').click().run()
        self.assertTrue(app.sidebar.error)
        self.assertEqual(app.text_input(key='personal_full_name').value, 'Alex Smith')
        app.sidebar.button(key='clear_data').click().run()
        self.assertEqual(app.text_input(key='personal_full_name').value, 'Alex Smith')
        app.button(key='confirm_clear').click().run()
        self.assertEqual(app.text_input(key='personal_full_name').value, '')
        self.assertEqual(app.session_state['education'], {})
        self.assertFalse(app.exception)
