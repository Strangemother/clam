from html.parser import HTMLParser
import unittest
from unittest.mock import patch

import server


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs).get("href"))


class IndexTests(unittest.TestCase):
    def test_index_links_to_browser_endpoints(self):
        client = server.app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "WebSocket YAML prompt demo", response.get_data(as_text=True)
        )
        parser = LinkParser()
        parser.feed(response.get_data(as_text=True))
        expected = {
            "/ui",
            "/ws/ui/",
            "/ws/images-ui",
            "/ws/yaml-ui",
            "/health",
            "/api/v1/models",
            "/ui/lm-studio/models",
        }
        self.assertEqual(set(parser.links), expected)
        with patch.object(server, "list_loaded_decision_models", return_value=[]):
            for link in parser.links:
                with self.subTest(link=link):
                    linked_response = client.get(link)
                    self.assertEqual(linked_response.status_code, 200)
                    linked_response.close()


class WebSocketUITests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_template_pages_are_served_at_both_slash_forms(self):
        cases = (
            ("/ws/ui", 'id="message"'),
            ("/ws/ui/", 'id="message"'),
            ("/ws/images-ui", 'id="image"'),
            ("/ws/images-ui/", 'id="image"'),
            ("/ws/yaml-ui", 'id="state"'),
            ("/ws/yaml-ui/", 'id="state"'),
        )
        for path, control in cases:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, "text/html")
                html = response.get_data(as_text=True)
                self.assertIn(control, html)
                self.assertIn(
                    'href="/static/websocket_demo.css"', html
                )
                self.assertIn('src="/static/websocket_demo.js"', html)
                self.assertNotIn("<style", html)
                self.assertNotIn("<script>", html)
                response.close()

    def test_shared_assets_are_available(self):
        for filename in ("websocket_demo.css", "websocket_demo.js"):
            with self.subTest(filename=filename):
                response = self.client.get(f"/static/{filename}")
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.data)
                response.close()

    def test_existing_prompt_ui_remains_available(self):
        response = self.client.get("/ui")
        self.assertEqual(response.status_code, 200)

    def test_yaml_page_lists_existing_prompts(self):
        response = self.client.get("/ws/yaml-ui")
        html = response.get_data(as_text=True)
        self.assertIn('value="chromite.d.yaml"', html)
        self.assertIn('id="prompt-content" readonly', html)
        self.assertIn('id="image" type="file"', html)
        self.assertIn("/ui/api/prompts/prompt-placeholder", html)


if __name__ == "__main__":
    unittest.main()
