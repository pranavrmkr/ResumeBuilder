import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from local_config import load_local_env


class LocalConfigTest(unittest.TestCase):
    def test_loading_quotes_and_restricted_names(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            path.write_text('# comment\nAI_PROVIDER=nvidia\nNVIDIA_API_KEY="test-only"\nNVIDIA_MODEL=example/model\nPATH=ignored\n', encoding='utf-8')
            with patch.dict(os.environ, {}, clear=True):
                load_local_env(path)
                self.assertEqual(os.environ['NVIDIA_API_KEY'], 'test-only')
                self.assertNotIn('AI_PROVIDER', os.environ)
                self.assertNotIn('PATH', os.environ)

    def test_shell_settings_take_precedence(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            path.write_text('NVIDIA_MODEL=local/model\n', encoding='utf-8')
            with patch.dict(os.environ, {'NVIDIA_MODEL': 'shell/model'}):
                load_local_env(path)
                self.assertEqual(os.environ['NVIDIA_MODEL'], 'shell/model')
            load_local_env(Path(folder) / 'missing')
