import unittest

import app


class TestPromptingPyFuncs(unittest.TestCase):
    def test_function_catalogue_loads_without_bulb_service(self):
        response = app.app.test_client().get("/prompting/functions/")

        self.assertEqual(response.status_code, 200)
        functions = response.get_json()
        names = {function["name"] for function in functions}
        self.assertIn("echo", names)
        self.assertIn("simple_bulb_perform", names)


if __name__ == "__main__":
    unittest.main()
