from test_navigation import navigate, open_summary_rewrite
from copy import deepcopy
from io import BytesIO
import json
import os
import unittest
from unittest.mock import patch, Mock
from streamlit.testing.v1 import AppTest
from ai_service import AIError
from bulk_ai import batches, validate_batch, apply_review
from profiles import initialise, restore, snapshot, checkpoint, travel
from test_upgrade import rich_profile


@patch.dict(os.environ, {'NVIDIA_API_KEY': 'test-key'})
class BulkTest(unittest.TestCase):
    def test_every_writing_section_and_protected_fields(self):
        p = rich_profile()
        p['education']['e']['details'] = 'studied coding subjects'
        fields = {k:v for group in batches(p).values() for k,v in group.items()}
        for section in ('personal_info','education','experience','skills','projects','achievements','additional'):
            self.assertTrue(any(k.startswith(section + '/') for k in fields), section)
        for path in fields:
            self.assertNotIn(path.split('/')[-1], ('email','phone','full_name','url','start_date','end_date','company','degree','issuer'))
        self.assertNotIn('zoe@example.com',json.dumps(fields))

    def test_batch_validation_is_complete_and_factual(self):
        original={'skills/s/name':'javascript basics','experience/x/achievements':'wrote unit tests for Python APIs'}
        updated={'skills/s/name':'JavaScript (Basic)','experience/x/achievements':'Wrote unit tests for Python APIs.'}
        self.assertEqual(validate_batch(json.dumps(updated),original),updated)
        for bad in ({}, {**updated,'extra':'value'}, {**updated,'skills/s/name':'JavaScript expert'},
                    {**updated,'experience/x/achievements':'Improved Python APIs by 80%.'},
                    {**updated,'experience/x/achievements':'Built Docker containers.'}):
            with self.subTest(bad=bad), self.assertRaises(AIError):
                validate_batch(json.dumps(bad),original)
        self.assertEqual(validate_batch(json.dumps({'skills/s/name':'REST API development'}), {'skills/s/name':'making rest apis'})['skills/s/name'],'REST API development')

    def test_project_stack_is_evidence_only_for_its_own_project(self):
        original = {'projects/a/description': 'made a task website', 'projects/a/technologies': 'Python, Flask',
                    'projects/b/description': 'made a report', 'projects/b/technologies': 'SQL'}
        good = dict(original, **{'projects/a/description': 'Developed a task application using Python and Flask.'})
        self.assertEqual(validate_batch(json.dumps(good), original), good)
        bad = dict(good, **{'projects/a/description': 'Built SQL reports.'})
        with self.assertRaises(AIError):
            validate_batch(json.dumps(bad), original)
        profile = rich_profile()
        profile['projects']['second'] = dict(profile['projects']['p'], title='Second project')
        for label, fields in batches(profile).items():
            if label.startswith('projects'):
                self.assertEqual(len({p.split('/')[1] for p in fields}), 1)

    def test_atomic_apply_stale_and_undo(self):
        state={}; initialise(state); restore(state,rich_profile()); checkpoint(state)
        original=snapshot(state)
        state['bulk_review']={'original':original,'changes':{'education/e/details':'Relevant coursework.'}}
        state['personal_info']['headline']='Changed'
        apply_review(state)
        self.assertEqual(state['education']['e']['details'],'')
        restore(state,original)
        state['bulk_review']={'original':original,'changes':{'education/e/details':'Relevant coursework.','projects/p/title':'Resume Workspace'}}
        apply_review(state); checkpoint(state)
        self.assertEqual(state['projects']['p']['title'],'Resume Workspace')
        self.assertEqual(state['education']['e']['details'],'Relevant coursework.')
        travel(state,'undo')
        self.assertEqual(state['projects']['p']['title'],original['projects']['p']['title'])

    def app(self):
        app=AppTest.from_string("from pathlib import Path\nexec(Path('app.py').read_text(encoding='utf-8-sig'))\nst.button('Load',key='load_test',on_click=load_saved_profile,args=('incoming',))",default_timeout=30).run()
        profile=rich_profile()
        profile['education']['e']['details']='studied coding subjects'
        app.session_state['incoming']=BytesIO(json.dumps(profile).encode())
        app.button(key='load_test').click().run()
        navigate(app, 'Improve entire resume')
        return app

    def test_ui_generate_apply_all_sections_and_no_auto_calls(self):
        def fake(original, section, provider, style, length):
            return {path: value + ' Revised.' for path,value in original.items()}, ()
        with patch('bulk_ai.improve_batch',side_effect=fake) as call:
            app=self.app()
            call.assert_not_called()
            self.assertFalse(app.button(key='bulk_generate').disabled)
            before=deepcopy(app.session_state['personal_info'])

            app.button(key='bulk_generate').click().run()
            self.assertGreater(call.call_count,5)
            self.assertEqual(app.session_state['personal_info'],before)
            app.button(key='bulk_apply').click().run()
            for section in ('education','experience','skills','projects','achievements'):
                self.assertTrue(any('Revised.' in v for entry in app.session_state[section].values() for v in entry.values()),section)
            self.assertIn('Revised.',app.session_state['additional']['languages'])
            self.assertEqual(app.session_state['personal_info']['email'],before['email'])
            navigate(app, 'Education')
            self.assertFalse(app.exception)

    def test_ui_failed_batch_is_reported_and_preserved(self):
        with patch('bulk_ai.improve_batch',side_effect=AIError('Test unavailable')):
            app=self.app()

            app.button(key='bulk_generate').click().run()
            self.assertTrue(app.session_state['bulk_review']['errors'])
            self.assertFalse(app.session_state['bulk_review']['changes'])
            self.assertTrue(app.button(key='bulk_apply').disabled)
            app.button(key='bulk_discard').click().run()
            self.assertNotIn('bulk_review',app.session_state)
            self.assertFalse(app.exception)
