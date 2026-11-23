from test_navigation import navigate, open_summary_rewrite
"""NVIDIA NIM transport and UI tests; no live requests or credentials required."""
import json
import os
import unittest
from io import StringIO
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError
from streamlit.testing.v1 import AppTest
from ai_service import (AIError, NvidiaProvider, WritingRequest,
                        list_nvidia_models, improve)


def response(payload):
    mock = MagicMock()
    mock.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    return mock


def completion(text='Developed Python tools.', reason='stop'):
    return {'choices': [{'finish_reason': reason, 'message': {'content': json.dumps({'text': text, 'questions': []})}}]}


class NvidiaTest(unittest.TestCase):
    def test_current_default_and_smoke_script(self):
        import check_nvidia
        from ai_service import NVIDIA_DEFAULT_MODEL
        with patch.dict(os.environ, {'NVIDIA_API_KEY': 'private-test', 'NVIDIA_MODEL': NVIDIA_DEFAULT_MODEL}), patch('sys.argv', ['check_nvidia.py']), patch('ai_service.urlopen', return_value=response(completion())) as call, redirect_stdout(StringIO()) as output:
            self.assertEqual(check_nvidia.main(), 0)
            body = json.loads(call.call_args.args[0].data)
            self.assertEqual(body['model'], NVIDIA_DEFAULT_MODEL)
            self.assertFalse(body['chat_template_kwargs']['enable_thinking'])
            self.assertNotIn('private-test', output.getvalue())
        with patch('ai_service.urlopen', side_effect=HTTPError('url', 410, 'private-test', {}, None)), self.assertRaisesRegex(AIError, 'retired'):
            NvidiaProvider(api_key='private-test').suggest(WritingRequest('Built tools.', 'projects'))

    def test_smoke_script_retirement_and_model_override(self):
        import check_nvidia
        with patch.dict(os.environ, {'NVIDIA_API_KEY': 'private-test'}), patch('sys.argv', ['check_nvidia.py', '--model', 'example/retired']), patch('ai_service.urlopen', side_effect=HTTPError('url', 410, 'private-test', {}, None)) as call, redirect_stdout(StringIO()) as output:
            self.assertEqual(check_nvidia.main(), 1)
            self.assertEqual(json.loads(call.call_args_list[0].args[0].data)['model'], 'example/retired')
            self.assertIn('retired', output.getvalue())
            self.assertNotIn('private-test', output.getvalue())

    def test_chat_transport_and_validated_result(self):
        with patch('ai_service.urlopen', return_value=response(completion())) as call:
            result = improve(WritingRequest('Built Python tools.', 'projects'), consent=True,
                             provider=NvidiaProvider(api_key='test-secret', model='example/model'))
        self.assertEqual(result.text, 'Developed Python tools.')
        request = call.call_args.args[0]
        self.assertEqual(request.full_url, 'https://integrate.api.nvidia.com/v1/chat/completions')
        body = json.loads(request.data)
        self.assertEqual(body['model'], 'example/model')
        self.assertFalse(body['stream'])
        self.assertEqual(body['messages'][0]['role'], 'system')
        self.assertIn('Never invent', body['messages'][0]['content'])
        self.assertNotIn('test-secret', request.data.decode())
        self.assertNotIn('store', body)

    def test_bad_outputs_and_unsupported_facts(self):
        for payload in ([], {'choices': []}, completion(reason='length'), completion(text='Built Docker tools.'),
                        completion(text='Improved results by 40%.'), {'choices': [{'finish_reason':'stop','message':{'content':None}}]}):
            with self.subTest(payload=payload), patch('ai_service.urlopen', return_value=response(payload)), self.assertRaises(AIError):
                NvidiaProvider(api_key='test').suggest(WritingRequest('Built Python tools.', 'projects'))

    def test_single_json_fence_supported(self):
        payload = completion()
        payload['choices'][0]['message']['content'] = '```json\n' + payload['choices'][0]['message']['content'] + '\n```'
        with patch('ai_service.urlopen', return_value=response(payload)):
            self.assertEqual(NvidiaProvider(api_key='test').suggest(WritingRequest('Built Python tools.', 'projects')).text, 'Developed Python tools.')

    def test_missing_key_consent_and_provider_selection(self):
        with patch('ai_service.urlopen') as call:
            with self.assertRaisesRegex(AIError, 'NVIDIA_API_KEY'):
                NvidiaProvider(api_key='').suggest(WritingRequest('Built tools.', 'projects'))
            with self.assertRaises(AIError):
                improve(WritingRequest('Built tools.', 'projects'), provider=NvidiaProvider(api_key='test'))
            call.assert_not_called()

    def test_safe_transport_errors(self):
        for error in (HTTPError('url',403,'private-key',{},None),HTTPError('url',429,'private-key',{},None),URLError('private-key')):
            with patch('ai_service.urlopen', side_effect=error), self.assertRaises(AIError) as raised:
                NvidiaProvider(api_key='private-key').suggest(WritingRequest('Built tools.', 'projects'))
            self.assertNotIn('private-key',str(raised.exception))

    def test_retired_model_falls_back_and_reuses_working_model(self):
        provider = NvidiaProvider(api_key='test', model='example/retired')
        request = WritingRequest('Built Python tools.', 'projects')
        with patch('ai_service.urlopen', side_effect=[
            HTTPError('url', 410, '', {}, None), response(completion()), response(completion())
        ]) as call:
            provider.suggest(request)
            provider.suggest(request)
        used = [json.loads(request.args[0].data)['model'] for request in call.call_args_list]
        self.assertEqual(used, [provider.model, provider.models[1], provider.models[1]])
        self.assertEqual(provider.last_model, provider.models[1])

    def test_invalid_key_stops_before_fallback(self):
        error = HTTPError('url', 401, 'private-key', {}, None)
        with patch('ai_service.urlopen', side_effect=error) as call:
            with self.assertRaisesRegex(AIError, 'NVIDIA_API_KEY'):
                NvidiaProvider(api_key='private-key').suggest(WritingRequest('Built tools.', 'projects'))
        call.assert_called_once()

    def test_batch_schema_requires_exact_fields_and_accepts_object(self):
        from bulk_ai import improve_batch
        fields = {'personal_info/headline': 'Python student'}
        payload = completion()
        payload['choices'][0]['message']['content'] = json.dumps(
            {'text': fields, 'questions': []})
        with patch('ai_service.urlopen', return_value=response(payload)) as call:
            result, _ = improve_batch(fields, 'personal_info', NvidiaProvider(api_key='test'))
        self.assertEqual(result, fields)
        schema = json.loads(call.call_args.args[0].data)['response_format']['json_schema']['schema']
        self.assertEqual(schema['properties']['text']['required'], list(fields))
        self.assertFalse(schema['properties']['text']['additionalProperties'])

    def test_bad_batch_mapping_tries_next_model(self):
        from bulk_ai import improve_batch
        provider = NvidiaProvider(api_key='test', model='example/preferred')
        field = 'projects/item/description'
        original = {field: 'Built Python tools.'}
        valid = {field: 'Developed Python tools.'}
        with patch('ai_service.urlopen', side_effect=[response(completion('{}')),
                                                    response(completion(json.dumps(valid)))]) as call:
            self.assertEqual(improve_batch(original, 'projects', provider), (valid, ()))
        self.assertEqual(call.call_count, 2)

    def test_catalog_lookup_and_failures(self):
        with patch.dict(os.environ, {'NVIDIA_API_KEY':'test'}):
            with patch('ai_service.urlopen',return_value=response({'data':[{'id':'b/model'},{'id':'a/model'},{'id':'a/model'},{}]})) as call:
                self.assertEqual(list_nvidia_models(),['a/model','b/model'])
                self.assertEqual(call.call_args.args[0].full_url,'https://integrate.api.nvidia.com/v1/models')
                self.assertIsNone(call.call_args.args[0].data)
            for payload in ([], {'data':[]}, {'data':None}):
                with patch('ai_service.urlopen',return_value=response(payload)), self.assertRaises(AIError):
                    list_nvidia_models()

    def test_ui_catalog_consent_and_key_not_exported(self):
        with patch.dict(os.environ, {'NVIDIA_API_KEY':'test-private', 'AI_PROVIDER':'nvidia'}), patch('ai_service.urlopen') as network:
            app = AppTest.from_file('app.py', default_timeout=15).run()
            self.assertFalse(app.exception)
            open_summary_rewrite(app)
            self.assertTrue(app.selectbox(key='writing_nvidia_choice'))
            network.assert_not_called()
            app.text_area(key='personal_summary').input('Built Python tools.').run()

            with patch('ai_ui.list_nvidia_models',return_value=['example/chat']):
                app.button(key='load_nvidia_models').click().run()
            app.selectbox(key='writing_nvidia_choice').select('example/chat').run()


            with patch('ai_service.urlopen', side_effect=[URLError('timeout'), response(completion())]) as call:
                app.button(key='ai_generate_personal_summary').click().run()
            self.assertEqual(call.call_count, 2)
            self.assertEqual(app.text_area(key='personal_summary').value,'Built Python tools.')
            app.button(key='ai_accept_personal_summary').click().run()
            self.assertEqual(app.text_area(key='personal_summary').value,'Developed Python tools.')

            from profiles import snapshot
            self.assertNotIn('test-private',json.dumps(snapshot(app.session_state)))
            self.assertFalse(app.exception)


if __name__ == '__main__':
    unittest.main()

