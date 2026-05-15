import unittest
from unittest.mock import patch, MagicMock
import prompting_proxy

class TestPromptingProxy(unittest.TestCase):
    def test_lmstudio_model_is_loaded(self):
        # Sample payload based on the description
        mock_payload = {
            "models": [
                {
                    "id": "granite-4.1-8b",
                    "loaded_instances": [
                        {
                            "identifier": "granite-4.1-8b",
                            "status": "loaded"
                        }
                    ]
                },
                {
                    "id": "granite-4.1-3b-abliterated",
                    "loaded_instances": []
                }
            ]
        }

        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_payload
            mock_get.return_value = mock_response

            cfg = {"lms_url": "http://localhost:1234"}
            headers = {}

            # Test case 1: granite-4.1-8b -> True
            res1 = prompting_proxy._lmstudio_model_is_loaded(cfg, "granite-4.1-8b", headers)
            print(f"Case 1: {res1}")
            self.assertTrue(res1)
            
            # Test case 2: granite-4.1-3b-abliterated -> False
            res2 = prompting_proxy._lmstudio_model_is_loaded(cfg, "granite-4.1-3b-abliterated", headers)
            print(f"Case 2: {res2}")
            self.assertFalse(res2)

    def test_lmstudio_list_models(self):
        mock_payload = {
            "models": [
                {"id": "model1"},
                {"id": "model2"}
            ]
        }
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_payload
            mock_get.return_value = mock_response
            
            cfg = {"lms_url": "http://localhost:1234"}
            headers = {}

            # Test case 3: _lmstudio_list_models can parse {models:[...]} successfully
            models = prompting_proxy._lmstudio_list_models(cfg, headers)
            print(f"Case 3 (list models): {models}")
            self.assertEqual(models, mock_payload["models"])

if __name__ == '__main__':
    unittest.main()
