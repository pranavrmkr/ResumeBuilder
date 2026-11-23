from test_navigation import navigate, open_summary_rewrite
from io import BytesIO
import unittest
import pdfplumber

from streamlit.testing.v1 import AppTest

from resume_upload import extract_resume_text, parse_resume_text, parse_entries, resume_sections


class ResumeUploadTest(unittest.TestCase):
    def test_full_resume_import_preview_and_pdf(self):
        text = """Maya Patel
maya@example.com
+91 90000 00002

Summary
Python engineer building reliable services.

Education
Example University
MSc
Computer Science
Aug 2017
May 2019
Graduated with distinction.

Sample College
BSc
Computer Science
Aug 2014
May 2017
Programming club leader.

Work Experience
Example Cloud Systems
Senior Python Engineer
Pune
Jul 2023
Present
Built reporting APIs.
Mentored three developers.

Sample Data Labs
Python Developer
Remote
Jun 2021
Jun 2023
Built ETL pipelines.
"""
        app = AppTest.from_string(
            "from pathlib import Path\nimport streamlit as st\n"
            "from resume_upload import import_uploaded_resume\n"
            "st.button('Import', key='test_import', on_click=import_uploaded_resume, args=('incoming',))\n"
            "exec(Path('app.py').read_text(encoding='utf-8'))\n"
        ).run()
        upload = BytesIO(text.encode())
        upload.name = 'resume.txt'
        app.session_state['incoming'] = upload
        app.button(key='test_import').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state['education']), 2)
        self.assertEqual(len(app.session_state['experience']), 2)
        for value in ('Example University', 'Sample College', 'Senior Python Engineer', 'Built ETL pipelines'):
            self.assertIn(value, app.markdown[-1].value)
        navigate(app, 'Education')
        entry = next(iter(app.session_state['education']))
        self.assertEqual(app.text_input(key=f'education_{entry}_degree').value, 'MSc')
        app.text_input(key=f'education_{entry}_institution').input('Edited University').run()
        self.assertIn('Edited University', app.markdown[-1].value)
        navigate(app, 'Experience')
        job = next(iter(app.session_state['experience']))
        self.assertEqual(app.text_input(key=f'experience_{job}_job_title').value, 'Senior Python Engineer')
        app.text_input(key=f'experience_{job}_company').input('Edited Company').run()
        navigate(app, 'Preview')
        next(button for button in app.button if button.label == 'Generate PDF').click().run()
        with pdfplumber.open(BytesIO(app.session_state['generated_pdf'][0])) as pdf:
            rendered = '\n'.join(page.extract_text() for page in pdf.pages)
        for value in ('Edited University', 'Edited Company', 'MSc', 'Built ETL pipelines'):
            self.assertIn(value, rendered)
        app.button(key='test_import').click().run()
        self.assertEqual(len(app.session_state['education']), 2)
        self.assertEqual(len(app.session_state['experience']), 2)
        self.assertIn('Example Cloud Systems', app.markdown[-1].value)
        self.assertNotIn('Edited Company', app.markdown[-1].value)
        self.assertFalse(app.exception)

    def test_labeled_sections_and_date_ranges(self):
        text = """EDUCATION:
Institution: Example University
Degree: BSc
Field of study: Computer Science
Start date: 2020
End date: 2024
Details: Graduated with honors.

Professional Experience:
Company: Example Co
Job title: Developer
Start date: 2024
End date: Present
Achievements:
- Built APIs
- Added tests
Skills
Python, SQL
"""
        sections = resume_sections(text)
        education = list(parse_entries(sections['education'], 'education').values())
        jobs = list(parse_entries(sections['experience'], 'experience').values())
        self.assertEqual(education[0]['institution'], 'Example University')
        self.assertEqual(jobs[0]['achievements'].strip(), 'Built APIs\nAdded tests')
        self.assertNotIn('Python', jobs[0]['achievements'])
        jobs = list(parse_entries('Developer\nExample Co\n2020 - Present\nBuilt tools.', 'experience').values())
        self.assertEqual(jobs[0]['start_date'], '2020')
        self.assertEqual(jobs[0]['end_date'], 'Present')
        self.assertEqual(jobs[0]['company'], 'Example Co')

    def test_parse_contact_details(self):
        cases = [
            ("RESUME\nPranav Ramkumar\npranav@example.com\n+91 98765 43210", {
                "full_name": "Pranav Ramkumar", "email": "pranav@example.com", "phone": "+91 98765 43210"}),
            ("Full Name: Ana O'Neil\nEmail: ana.oneil+work@example.co.uk\nPhone: (415) 555-1234", {
                "full_name": "Ana O'Neil", "email": "ana.oneil+work@example.co.uk", "phone": "(415) 555-1234"}),
            ("José García | jose@example.com\n2020 - 2024", {
                "full_name": "José García", "email": "jose@example.com"}),
            ("Education\n2020 - 2024\nSkills", {}),
            ("", {}),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(parse_resume_text(text), expected)

    def test_text_files_and_bad_uploads(self):
        for encoding in ("utf-8-sig", "utf-16"):
            upload = BytesIO("José García\njose@example.com".encode(encoding))
            upload.name = "resume.TXT"
            upload.seek(5)
            self.assertEqual(extract_resume_text(upload), "José García\njose@example.com")
        for name, content in (("empty.txt", b"  "), ("bad.pdf", b"not a pdf"),
                              ("bad.txt", b"\x80\x81"), ("resume.doc", b"Hello")):
            upload = BytesIO(content)
            upload.name = name
            with self.subTest(name=name), self.assertRaises(ValueError):
                extract_resume_text(upload)

    def test_pdf_text(self):
        content = b"BT /F1 12 Tf 72 720 Td (Alex Smith) Tj 0 -20 Td (alex@example.com) Tj ET"
        pdf = (
            b"%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
            b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
            b"5 0 obj << /Length " + str(len(content)).encode() + b" >> stream\n" + content
            + b"\nendstream endobj\ntrailer << /Root 1 0 R >>\n%%EOF"
        )
        upload = BytesIO(pdf)
        upload.name = "resume.pdf"
        self.assertEqual(parse_resume_text(extract_resume_text(upload)), {
            "full_name": "Alex Smith", "email": "alex@example.com"
        })

    def test_import_and_clear_forms(self):
        app = AppTest.from_string(
            "from pathlib import Path\n"
            "import streamlit as st\n"
            "from resume_upload import import_uploaded_resume\n"
            "st.button('Import test file', key='test_import', "
            "on_click=import_uploaded_resume, args=('incoming',))\n"
            "exec(Path('app.py').read_text(encoding='utf-8'))\n"
        ).run()
        app.text_input(key="personal_full_name").input("Old Name").run()
        app.text_input(key="personal_headline").input("Developer").run()
        upload = BytesIO(b"Alex Smith\nalex@example.com\n+91 98765 43210")
        upload.name = "resume.txt"
        app.session_state["incoming"] = upload
        app.button(key="test_import").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text_input(key="personal_full_name").value, "Alex Smith")
        self.assertEqual(app.text_input(key="personal_email").value, "alex@example.com")
        self.assertEqual(app.text_input(key="personal_phone").value, "+91 98765 43210")
        self.assertEqual(app.text_input(key="personal_headline").value, "Developer")
        app.text_input(key="personal_full_name").input("Edited Name").run()
        navigate(app, "Education")
        app.button[1].click().run()
        self.assertEqual(len(app.session_state["education"]), 1)
        navigate(app, "Personal Info")
        self.assertEqual(app.text_input(key="personal_full_name").value, "Edited Name")

        upload = BytesIO(b"updated@example.com")
        upload.name = "updated.txt"
        app.session_state["incoming"] = upload
        app.button(key="test_import").click().run()
        self.assertEqual(app.text_input(key="personal_full_name").value, "Edited Name")
        self.assertEqual(app.text_input(key="personal_email").value, "updated@example.com")
        upload = BytesIO(b"invalid pdf")
        upload.name = "invalid.pdf"
        app.session_state["incoming"] = upload
        app.button(key="test_import").click().run()
        self.assertTrue(app.sidebar.error)
        self.assertEqual(app.text_input(key="personal_email").value, "updated@example.com")

        app.sidebar.button(key="clear_data").click().run()
        self.assertEqual(app.text_input(key="personal_full_name").value, "Edited Name")
        app.button(key="confirm_clear").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text_input(key="personal_full_name").value, "")
        self.assertEqual(app.text_input(key="personal_email").value, "")
        self.assertEqual(app.text_input(key="personal_phone").value, "")
        self.assertEqual(app.session_state["education"], {})
        self.assertEqual(app.session_state["experience"], {})
        self.assertEqual(app.session_state["upload_version"], 1)
        self.assertEqual(app.get("file_uploader")[0].proto.id.split("-")[-1], "resume_upload_1")
