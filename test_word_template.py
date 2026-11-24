"""Word document integrity checks that do not require Microsoft Office."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from word_template import make_filled_docx, W


class WordTemplateTest(unittest.TestCase):
    def test_filled_document_keeps_compatibility_prefixes(self):
        with TemporaryDirectory() as directory:
            path = make_filled_docx(
                {'personal_info': {'full_name': 'Template Test', 'email': 'test@example.com'}},
                output_path=Path(directory) / 'resume.docx')
            with ZipFile(path) as document:
                for name in ('word/document.xml', 'word/styles.xml', 'word/theme/theme1.xml', 'word/numbering.xml'):
                    if name not in document.namelist():
                        continue
                    contents = document.read(name)
                    namespaces = {}
                    for event, item in ET.iterparse(BytesIO(contents), events=('start-ns', 'start')):
                        if event == 'start':
                            root = item
                            break
                        namespaces[item[0]] = item[1]
                    ignorable = root.get('{http://schemas.openxmlformats.org/markup-compatibility/2006}Ignorable', '')
                    self.assertTrue(set(ignorable.split()) <= namespaces.keys(), name)
                root = ET.fromstring(document.read('word/document.xml'))
                text = ''.join(node.text or '' for node in root.iter(f'{{{W}}}t'))
                self.assertIn('Template Test', text)
                self.assertIn('test@example.com', text)
