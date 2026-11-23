from test_navigation import navigate, open_summary_rewrite
import unittest

from streamlit.testing.v1 import AppTest


class ResumeAppTest(unittest.TestCase):
    def test_resume_workflow(self):
        app = AppTest.from_file("app.py").run()
        self.assertFalse(app.exception)
        self.assertIn("Your name", app.markdown[-1].value)
        app.text_input(key="personal_full_name").input("A *Builder*").run()
        app.text_input(key="personal_email").input("builder@example.com").run()
        self.assertIn(r"A \*Builder\*", app.markdown[-1].value)

        navigate(app, "Education")
        app.button[0].click().run()
        first_degree = next(iter(app.session_state["education"]))
        app.text_input(key=f"education_{first_degree}_institution").input("Example University").run()
        app.text_input(key=f"education_{first_degree}_degree").input("BSc").run()
        app.button[0].click().run()
        self.assertEqual(len(app.session_state["education"]), 2)
        self.assertIn("Example University", app.markdown[-1].value)

        navigate(app, "Experience")
        app.button[0].click().run()
        first_job = next(iter(app.session_state["experience"]))
        app.text_input(key=f"experience_{first_job}_company").input("Example Co").run()
        app.text_input(key=f"experience_{first_job}_job_title").input("Developer").run()
        app.text_area(key=f"experience_{first_job}_achievements").input("Built tools\n\nHelped users").run()
        app.button[0].click().run()
        self.assertEqual(len(app.session_state["experience"]), 2)

        navigate(app, "Preview")
        rendered = app.markdown[-1].value
        for expected in (r"builder@example\.com", "Example University", "Developer", "Example Co", "- Built tools\n- Helped users"):
            self.assertIn(expected, rendered)
        navigate(app, "Personal Info")
        self.assertEqual(app.text_input(key="personal_full_name").value, "A *Builder*")

        navigate(app, "Education")
        self.assertEqual(app.text_input(key=f"education_{first_degree}_degree").value, "BSc")
        app.button(key=f"remove_education_{first_degree}").click().run()
        self.assertEqual(len(app.session_state["education"]), 1)
        self.assertNotIn("Example University", app.markdown[-1].value)
        app.button[1].click().run()
        self.assertNotIn("## Education", app.markdown[-1].value)

        navigate(app, "Experience")
        self.assertEqual(app.text_input(key=f"experience_{first_job}_company").value, "Example Co")
        app.button(key=f"remove_experience_{first_job}").click().run()
        self.assertEqual(len(app.session_state["experience"]), 1)
        app.button[1].click().run()
        self.assertNotIn("## Experience", app.markdown[-1].value)
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
