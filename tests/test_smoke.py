import os
import tempfile
import unittest

class BasicProjectFilesTest(unittest.TestCase):
    def test_project_files_exist(self):
        base = os.path.dirname(os.path.dirname(__file__))
        for name in ["app.py", "database.py", "products.py", "requirements.txt"]:
            self.assertTrue(os.path.exists(os.path.join(base, name)))

if __name__ == "__main__":
    unittest.main()
