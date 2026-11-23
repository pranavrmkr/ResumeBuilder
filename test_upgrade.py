from test_navigation import navigate, open_summary_rewrite
"""Regression coverage for the integrated upgrade. All AI calls are mocked."""
from copy import deepcopy
from dataclasses import asdict
from io import BytesIO
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pdfplumber
from streamlit.testing.v1 import AppTest
from ai_service import AIError, WritingRequest, NvidiaProvider, improve, validate_suggestion
from analysis_tools import analyze_job, quality_check, completion
from exporter import generate_resume_pdf
from models import Skill, Project
from preview import resume_markdown, resume_blocks
from profiles import (normalise_profile, initialise, restore, snapshot, checkpoint,
                      travel, duplicate, switch, add_entry, move_entry, TEMPLATES)
from resume_upload import parse_new_entries, resume_sections


def rich_profile():
    return normalise_profile({
        'personal_info': {'full_name': 'Zoë Иванова', 'email': 'zoe@example.com',
                          'phone': '+91 90000 00000', 'headline': 'Software developer',
                          'summary': 'Python developer building accessible tools.', 'website': 'https://example.com'},
        'education': {'e': {'degree': 'BSc', 'institution': 'Example University', 'start_date': 'Aug 2020', 'end_date': 'May 2024'}},
        'experience': {'x': {'job_title': 'Developer', 'company': 'Example Co', 'achievements': 'Built Python APIs.\nAdded SQL reporting.'}},
        'skills': {'s': {'name': 'Python', 'category': 'Languages'}, 't': {'name': 'SQL', 'category': 'Databases', 'proficiency': 'Working knowledge'}},
        'projects': {'p': {'title': 'Résumé Studio', 'description': 'Built a Streamlit editor.', 'technologies': 'Python, Streamlit', 'contributions': 'Implemented profile imports.\nAdded PDF exports.', 'url': 'https://example.com/project'}},
        'certifications': {'c': {'name': 'Cloud fundamentals', 'issuer': 'Example Academy', 'date': '2024', 'url': 'https://example.com/credential'}},
        'achievements': {'a': {'title': 'Student showcase', 'description': 'Presented the editor.', 'date': '2024'}},
        'additional': {'languages': 'English, Français', 'github': 'https://github.com/example', 'extracurricular': 'Programming club'}})


def render(profile):
    return resume_markdown(profile['personal_info'], profile['education'], profile['experience'],
                           **{k: profile[k] for k in ('skills','projects','certifications','achievements','additional','settings')})


def pdf_bytes(profile):
    return generate_resume_pdf(profile['personal_info'], profile['education'], profile['experience'],
                                **{k: profile[k] for k in ('skills','projects','certifications','achievements','additional','settings')})


class ProfileTest(unittest.TestCase):
    def test_old_profile_defaults_and_roundtrip(self):
        old = {'personal_info': {'full_name': 'Alex'}, 'education': {}, 'experience': {}}
        p = normalise_profile(old)
        self.assertEqual(p['skills'], {})
        self.assertEqual(p['additional']['github'], '')
        self.assertEqual(normalise_profile(json.loads(json.dumps(rich_profile()))), rich_profile())

    def test_atomic_invalid_profile_restore(self):
        state = {}
        initialise(state)
        before = snapshot(state)
        for bad in ([], {'skills': []}, {'projects': {'a': []}}, {'settings': {'section_order': {}}}, {'format_version': 99}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                restore(state, bad)
            self.assertEqual(snapshot(state), before)

    def test_entry_operations(self):
        entries = {}
        first = add_entry(entries, Skill)
        entries[first]['name'] = 'Python'
        second = add_entry(entries, Skill)
        entries[second]['name'] = 'SQL'
        self.assertEqual(list(move_entry(entries, second, -1)), [second, first])
        entries[first]['name'] = 'Python 3'
        del entries[second]
        self.assertEqual(entries[first]['name'], 'Python 3')
        projects = {}
        key = add_entry(projects, Project)
        projects[key]['title'] = 'Editor'
        projects[key]['description'] = 'Built an editor.'
        self.assertEqual(projects[key]['title'], 'Editor')

    def test_history_and_profiles(self):
        state = {}
        initialise(state)
        checkpoint(state)
        state['personal_info']['full_name'] = 'Alex'
        checkpoint(state)
        duplicate(state, 'Role B')
        state['personal_info']['full_name'] = 'Sam'
        checkpoint(state)
        travel(state, 'undo')
        checkpoint(state)
        self.assertEqual(state['personal_info']['full_name'], 'Alex')
        travel(state, 'redo')
        self.assertEqual(state['personal_info']['full_name'], 'Sam')
        switch(state, 'My resume')
        self.assertEqual(state['personal_info']['full_name'], 'Alex')
        switch(state, 'Role B')
        self.assertEqual(state['personal_info']['full_name'], 'Sam')


class AnalysisTest(unittest.TestCase):
    def test_job_matching_boundaries_and_coverage(self):
        result = analyze_job(rich_profile(), 'Python SQL Docker C++ Java required')
        self.assertEqual(set(result['present']), {'Python', 'SQL'})
        self.assertEqual(result['coverage'], 40)
        self.assertIn('Docker', result['missing'])
        self.assertTrue(result['relevant'])
        self.assertIsNone(analyze_job(rich_profile(), '')['coverage'])
        self.assertNotIn('Java', analyze_job(normalise_profile({'personal_info': {'summary': 'JavaScript'}}), 'Java required')['present'])

    def test_quality_checks(self):
        p = normalise_profile({})
        issues = quality_check(p)
        self.assertTrue(any('email' in issue for issue in issues))
        self.assertTrue(any('skills' in issue for issue in issues))
        p = rich_profile()
        p['projects']['p']['description'] = 'word ' * 101
        p['projects']['p']['technologies'] = ''
        p['experience']['x']['start_date'] = '2024'
        p['experience']['x']['achievements'] = 'Built tools for my team.\nBuilt tools for my team.'
        issues = quality_check(p)
        for term in ('long', 'technologies', 'consistent dates', 'repeated'):
            self.assertTrue(any(term in i for i in issues), issues)
        self.assertEqual(sum(completion(rich_profile()).values()), 6)

    def test_hidden_skills_are_not_counted(self):
        p = rich_profile()
        p['settings']['hidden_sections'] = ['skills']
        p['personal_info']['summary'] = ''
        p['experience'], p['projects'] = {}, {}
        self.assertNotIn('SQL', analyze_job(p, 'SQL required')['present'])


class AITest(unittest.TestCase):
    def test_consent_before_provider(self):
        provider = unittest.mock.Mock()
        with self.assertRaises(AIError):
            improve(WritingRequest('Built tools', 'projects'), provider=provider)
        provider.suggest.assert_not_called()

    def test_missing_key(self):
        with self.assertRaisesRegex(AIError, 'NVIDIA_API_KEY'):
            improve(WritingRequest('Built tools', 'projects'), consent=True, provider=NvidiaProvider(api_key=''))

    def test_output_validation(self):
        self.assertEqual(validate_suggestion({'text': 'Built Python tools.', 'questions': []}, 'Python tools').text, 'Built Python tools.')
        for invalid in ({'text': '', 'questions': []}, {'text': 'Improved by 50%', 'questions': []},
                        {'text': 'Built Kubernetes tools.', 'questions': []},
                        {'text': 'Built tools.', 'questions': 'wrong'}, {'text': 'Built tools.'}):
            with self.subTest(invalid=invalid), self.assertRaises(AIError):
                validate_suggestion(invalid, 'Built tools.')

    def test_service_errors_are_safe(self):
        for error in (HTTPError('url', 401, 'secret-value', {}, None), HTTPError('url', 429, 'secret-value', {}, None),
                      URLError('secret-value'), TimeoutError('secret-value')):
            with self.subTest(error=error), patch('ai_service.urlopen', side_effect=error):
                with self.assertRaises(AIError) as raised:
                    NvidiaProvider(api_key='secret-value').suggest(WritingRequest('Built tools', 'projects'))
                self.assertNotIn('secret-value', str(raised.exception))

    def test_invalid_provider_payload_and_refusal(self):
        for payload in ([], {'choices': ['malformed']}, {'choices': []},
                        {'choices': [{'finish_reason': 'content_filter', 'message': {'content': None}}]}):
            response = unittest.mock.MagicMock()
            response.__enter__.return_value.read.return_value = json.dumps(payload).encode()
            with patch('ai_service.urlopen', return_value=response), self.assertRaises(AIError):
                NvidiaProvider(api_key='test').suggest(WritingRequest('Built tools', 'projects'))

    def test_job_requirements_are_not_candidate_evidence(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({'choices': [{'finish_reason': 'stop', 'message': {
            'content': json.dumps({'text': 'Built Docker tools for 5 years.', 'questions': []})}}]}).encode()
        with patch('ai_service.urlopen', return_value=response), self.assertRaises(AIError):
            NvidiaProvider(api_key='test').suggest(WritingRequest('Built tools.', 'projects', context=json.dumps({'existing_entry': {'description': 'Built tools.'}, 'job_description': 'Docker and 5 years required'})))


class RenderingTest(unittest.TestCase):
    def test_sections_hidden_and_ordered(self):
        p = rich_profile()
        text = render(p)
        for word in ('Python', 'Résumé Studio', 'Cloud fundamentals', 'Student showcase', 'Français'):
            self.assertIn(word, text)
        p['settings']['hidden_sections'] = ['certifications', 'achievements']
        self.assertNotIn('Cloud fundamentals', render(p))
        p['settings']['template'] = 'Technical Resume'
        text = render(p)
        self.assertLess(text.index('## Skills'), text.index('## Experience'))
        p['settings']['student_mode'] = True
        self.assertLess(render(p).index('## Education'), render(p).index('## Projects'))

    def test_unicode_all_templates_and_links(self):
        for template in TEMPLATES:
            p = rich_profile()
            p['settings']['template'] = template
            with self.subTest(template=template), pdfplumber.open(BytesIO(pdf_bytes(p))) as pdf:
                text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
                for word in ('Zoë Иванова', 'Résumé Studio', 'Français', 'Cloud fundamentals', 'Student showcase', 'Python'):
                    self.assertIn(word, text)
                links = [a.get('uri', '') for page in pdf.pages for a in page.hyperlinks]
                self.assertIn('https://example.com/project', links)
                self.assertIn('mailto:zoe@example.com', links)

    def test_multipage_wrapping_bounds_and_heading_orphans(self):
        p = rich_profile()
        p['experience'] = {str(i): {'job_title': f'Engineer {i}', 'company': 'Example Co', 'location': 'Remote',
            'start_date': '2020', 'end_date': 'Present', 'achievements': ('Built reliable services and collaborated on technical delivery. ' * 18 + '\n') * 3} for i in range(9)}
        p['projects']['p']['url'] = 'https://example.com/' + 'verylongidentifier' * 35
        for template in TEMPLATES:
            p['settings']['template'] = template
            with self.subTest(template=template), pdfplumber.open(BytesIO(pdf_bytes(p))) as pdf:
                self.assertGreater(len(pdf.pages), 2)
                text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
                self.assertIn('Engineer 8', text)
                self.assertIn('Student showcase', text)
                for page in pdf.pages:
                    for char in page.chars:
                        self.assertGreaterEqual(char['x0'], 40)
                        self.assertLessEqual(char['x1'], page.width - 39)
                        self.assertLess(char['bottom'], page.height - 15)
                    content = [line for line in (page.extract_text() or '').splitlines() if not line.startswith('Page ')]
                    self.assertNotIn(content[-1], ['EDUCATION', 'EXPERIENCE', 'SKILLS', 'PROJECTS', 'CERTIFICATIONS', 'ACHIEVEMENTS'])

    def test_unsupported_glyph_is_explicit(self):
        p = rich_profile()
        p['personal_info']['full_name'] = 'Name 🦄'
        with self.assertRaisesRegex(ValueError, 'does not cover'):
            pdf_bytes(p)

    def test_safe_markdown_links(self):
        p = rich_profile()
        p['projects']['p']['url'] = 'javascript:alert(1)'
        p['projects']['p']['title'] = '<script>alert(1)</script> *unsafe*'
        text = render(p)
        self.assertNotIn('](javascript:', text)
        self.assertIn(r'\*unsafe\*', text)


class NewUploadTest(unittest.TestCase):
    def test_new_labeled_sections(self):
        sections = resume_sections('Skills\nLanguages: Python | SQL\nProjects\nTitle: Tool\nDescription: Built an editor.\nTechnologies: Python\n\nTitle: CLI\nDescription: Built a CLI.\nCertifications\nName: Basics\nIssuer: Academy\nAchievements\nTitle: Showcase\nDescription: Presented tools.\nLanguages\nEnglish')
        self.assertEqual(len(parse_new_entries(sections['skills'], 'skills')), 2)
        self.assertEqual(len(parse_new_entries(sections['projects'], 'projects')), 2)
        self.assertEqual(next(iter(parse_new_entries(sections['certifications'], 'certifications').values()))['issuer'], 'Academy')
        self.assertEqual(next(iter(parse_new_entries(sections['achievements'], 'achievements').values()))['title'], 'Showcase')
        self.assertEqual(parse_new_entries('Unstructured project paragraph', 'projects'), {})


class UpgradeUITest(unittest.TestCase):
    def app(self):
        app = AppTest.from_file('app.py').run()
        self.assertFalse(app.exception)
        return app

    def test_skills_crud_navigation_and_json(self):
        app = self.app()
        navigate(app, 'Skills')
        next(b for b in app.button if b.label == 'Add skill').click().run()
        key = next(iter(app.session_state['skills']))
        app.text_input(key=f'skills_{key}_name').input('Python').run()
        app.text_input(key=f'skills_{key}_category').input('Languages').run()
        self.assertIn('Python', app.markdown[-1].value)
        navigate(app, 'Preview')
        navigate(app, 'Skills')
        self.assertEqual(app.text_input(key=f'skills_{key}_name').value, 'Python')
        app.text_input(key=f'skills_{key}_name').input('Rust').run()
        self.assertIn('Rust', app.markdown[-1].value)
        app.button(key=f'remove_skills_{key}').click().run()
        self.assertNotIn('## Skills', app.markdown[-1].value)

    def test_projects_certifications_and_achievements(self):
        app = self.app()
        for section, name_field, value in [('projects', 'title', 'Resume tool'), ('certifications', 'name', 'Fundamentals'), ('achievements', 'title', 'Showcase')]:
            navigate(app, section.title())
            next(b for b in app.button if b.label.startswith('Add ')).click().run()
            key = next(iter(app.session_state[section]))
            app.text_input(key=f'{section}_{key}_{name_field}').input(value).run()
            self.assertIn(value, app.markdown[-1].value)
            self.assertFalse(app.exception)

    def test_template_visibility_and_clear_cancel(self):
        app = self.app()
        app.text_input(key='personal_full_name').input('Alex').run()
        navigate(app, 'Preview')
        app.selectbox(key='layout_template').select('Technical Resume').run()
        self.assertEqual(app.session_state['settings']['template'], 'Technical Resume')
        app.sidebar.button(key='clear_data').click().run()
        app.button(key='cancel_clear').click().run()
        self.assertEqual(app.session_state['personal_info']['full_name'], 'Alex')
        app.sidebar.button(key='clear_data').click().run()
        app.button(key='confirm_clear').click().run()
        self.assertEqual(app.session_state['skills'], {})
        self.assertFalse(app.exception)

    def test_ai_review_accept_reject_and_no_automatic_calls(self):
        from ai_service import Suggestion
        app = self.app()
        app.text_area(key='personal_summary').input('Built Python tools').run()
        open_summary_rewrite(app)
        with patch('ai_ui.improve', return_value=Suggestion('Developed Python tools.')) as mocked:
            app.run()
            mocked.assert_not_called()

            app.button(key='ai_generate_personal_summary').click().run()
            self.assertEqual(app.text_area(key='personal_summary').value, 'Built Python tools')
            app.button(key='ai_accept_personal_summary').click().run()
            self.assertEqual(app.text_area(key='personal_summary').value, 'Developed Python tools.')
            app.button(key='ai_generate_personal_summary').click().run()
            app.button(key='ai_reject_personal_summary').click().run()
            self.assertNotIn('ai_result_personal_summary', app.session_state)
            self.assertEqual(mocked.call_count, 2)
        self.assertFalse(app.exception)

    def test_new_sections_import_callback(self):
        app = AppTest.from_string("from pathlib import Path\nfrom resume_upload import import_uploaded_resume\nimport streamlit as st\nst.button('Import', key='test_import', on_click=import_uploaded_resume,args=('incoming',))\nexec(Path('app.py').read_text(encoding='utf-8-sig'))").run()
        upload = BytesIO(b'Alex Smith\nSkills\nTools: Git | Docker\nProjects\nTitle: CLI\nDescription: Built a tool.\nLanguages\nEnglish')
        upload.name = 'resume.txt'
        app.session_state['incoming'] = upload
        app.button(key='test_import').click().run()
        self.assertEqual(len(app.session_state['skills']), 2)
        self.assertEqual(len(app.session_state['projects']), 1)
        self.assertIn('English', app.markdown[-1].value)
        self.assertFalse(app.exception)

    def test_workspace_history_panel_removed(self):
        app = self.app()
        self.assertFalse(any(e.label == 'Workspace & history' for e in app.expander))
        self.assertFalse(any(b.label in ('Undo', 'Redo', 'Duplicate resume') for b in app.button))
        self.assertFalse(app.exception)

    def test_project_reorder_and_json_restores_every_section(self):
        p = rich_profile()
        app = AppTest.from_string("from pathlib import Path\nexec(Path('app.py').read_text(encoding='utf-8-sig'))\nst.button('Load',key='load_test',on_click=load_saved_profile,args=('incoming',))\nst.session_state['saved_json']=json_data").run()
        app.session_state['incoming'] = BytesIO(json.dumps(p).encode())
        app.button(key='load_test').click().run()
        self.assertEqual(json.loads(app.session_state['saved_json']), p)
        navigate(app, 'Projects')
        next(b for b in app.button if b.label == 'Add project').click().run()
        keys = list(app.session_state['projects'])
        app.button(key=f'projects_{keys[1]}_move-1').click().run()
        self.assertEqual(list(app.session_state['projects']), keys[::-1])
        self.assertFalse(app.exception)

    def test_summary_generation_uses_evidence_and_requires_acceptance(self):
        from ai_service import Suggestion
        app = self.app()
        navigate(app, 'Summary assistant')
        self.assertTrue(app.button(key='ai_generate_personal_summary').disabled)
        navigate(app, 'Personal Info')
        app.text_input(key='personal_headline').input('Python developer').run()
        app.text_input(key='personal_email').input('private@example.com').run()
        navigate(app, 'Summary assistant')

        with patch('ai_ui.improve', return_value=Suggestion('Python developer.')) as mock:
            app.button(key='ai_generate_personal_summary').click().run()
        request = mock.call_args.args[0]
        self.assertEqual(request.action, 'Generate summary')
        self.assertIn('Python developer', request.text)
        self.assertNotIn('private@example.com', request.text)
        self.assertEqual(app.session_state['personal_info']['summary'], '')
        app.button(key='ai_accept_personal_summary').click().run()
        self.assertEqual(app.session_state['personal_info']['summary'], 'Python developer.')
        self.assertFalse(app.exception)

    def test_local_job_analyzer_ui_and_stale_result(self):
        app = self.app()
        app.text_area(key='personal_summary').input('Python developer').run()
        navigate(app, 'Review & Match')
        app.text_area(key='job_description').input('Python and Docker required').run()
        next(b for b in app.button if b.label == 'Analyze job description').click().run()
        self.assertEqual(app.session_state['job_analysis'][2]['coverage'], 50)
        app.text_area(key='job_description').input('SQL required').run()
        self.assertTrue(any('changed' in i.value for i in app.info))
        self.assertFalse(app.exception)


if __name__ == '__main__':
    unittest.main()
