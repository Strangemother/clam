"""
test_save_layout_endpoint.py
──────────────────────────────────────────────────────────────────────────────
Tests for the POST /api/layout/save Flask endpoint added in app.py.

Coverage
────────
  1. Valid save — correct body produces a JSON file in LAYOUTS_DIR.
  2. Name sanitisation — slashes, dots, special chars stripped; spaces → hyphens.
  3. Missing name field → 400 error.
  4. Blank name after strip → 400 error.
  5. Name with only invalid chars → 400 error.
  6. No JSON body → 400 error.
  7. Layout content (nodes / connections / edges) written verbatim.
  8. Saving twice with the same name overwrites the file (no duplicate suffix).

Run:
    cd power_graph && python -m pytest tests/test_save_layout_endpoint.py -v
"""

import json
import pathlib
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))

# Import app under test — patch LAYOUTS_DIR before any request is made.
import importlib
import power_graph.nodes  # noqa — registers node types (needed by app import)


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def client(tmp_path):
    """
    Flask test client with LAYOUTS_DIR redirected to a temp directory so tests
    never touch the real func-pipes/layouts folder.
    """
    import app as app_module
    app_module.LAYOUTS_DIR = tmp_path          # redirect writes
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c, tmp_path


# ── Helper ────────────────────────────────────────────────────────────────────

def _post(client, body):
    return client.post(
        '/api/layout/save',
        data=json.dumps(body),
        content_type='application/json',
    )


MINIMAL_LAYOUT = {
    'name':        'my-layout',
    'nodes':       [{'id': 1, 'type': 'gen', 'title': 'G', 'config': {}}],
    'connections': [],
    'edges':       {},
}


# ── Happy-path tests ──────────────────────────────────────────────────────────

class TestSaveLayoutHappyPath:

    def test_returns_200_and_saved_filename(self, client):
        c, _ = client
        res  = _post(c, MINIMAL_LAYOUT)
        assert res.status_code == 200
        body = res.get_json()
        assert body['saved'] == 'my-layout.json'

    def test_file_created_in_layouts_dir(self, client):
        c, tmp = client
        _post(c, MINIMAL_LAYOUT)
        assert (tmp / 'my-layout.json').exists()

    def test_file_content_is_valid_json(self, client):
        c, tmp = client
        _post(c, MINIMAL_LAYOUT)
        content = json.loads((tmp / 'my-layout.json').read_text())
        assert isinstance(content, dict)
        assert 'nodes' in content
        assert 'connections' in content
        assert 'edges' in content

    def test_nodes_connections_edges_written_verbatim(self, client):
        c, tmp = client
        body = {
            'name':        'verbatim',
            'nodes':       [{'id': 99, 'type': 'heater'}],
            'connections': [{'sender': {'label': 1}, 'receiver': {'label': 99}}],
            'edges':       {'1-0-99-0': {'wireType': 'copper', 'length': 100}},
        }
        _post(c, body)
        content = json.loads((tmp / 'verbatim.json').read_text())
        assert content['nodes'][0]['id'] == 99
        assert content['connections'][0]['receiver']['label'] == 99
        assert content['edges']['1-0-99-0']['length'] == 100

    def test_overwrite_on_duplicate_name(self, client):
        c, tmp = client
        _post(c, {**MINIMAL_LAYOUT, 'nodes': [{'id': 1}]})
        _post(c, {**MINIMAL_LAYOUT, 'nodes': [{'id': 2}]})
        content = json.loads((tmp / 'my-layout.json').read_text())
        # Second write must overwrite, not create a second file
        files = list(tmp.iterdir())
        assert len(files) == 1
        assert content['nodes'][0]['id'] == 2


# ── Name sanitisation tests ───────────────────────────────────────────────────

class TestNameSanitisation:

    def _saved_name(self, client, name):
        c, tmp = client
        res  = _post(c, {**MINIMAL_LAYOUT, 'name': name})
        assert res.status_code == 200, res.get_json()
        return res.get_json()['saved'], tmp

    def test_spaces_become_hyphens(self, client):
        saved, tmp = self._saved_name(client, 'my layout name')
        assert saved == 'my-layout-name.json'
        assert (tmp / saved).exists()

    def test_special_chars_stripped(self, client):
        saved, tmp = self._saved_name(client, 'layout/test..bad!@#')
        # slashes, dots, !, @, # removed; remaining alphanum preserved
        assert '/' not in saved
        assert '.' in saved and saved.endswith('.json')  # only the .json dot remains
        assert (tmp / saved).exists()

    def test_leading_trailing_whitespace_stripped(self, client):
        saved, _ = self._saved_name(client, '  my-layout  ')
        assert saved == 'my-layout.json'

    def test_underscores_preserved(self, client):
        saved, _ = self._saved_name(client, 'my_layout_v2')
        assert saved == 'my_layout_v2.json'

    def test_hyphens_preserved(self, client):
        saved, _ = self._saved_name(client, 'my-layout-v2')
        assert saved == 'my-layout-v2.json'


# ── Error cases ───────────────────────────────────────────────────────────────

class TestSaveLayoutErrors:

    def test_missing_name_returns_400(self, client):
        c, _ = client
        res  = _post(c, {'nodes': [], 'connections': [], 'edges': {}})
        assert res.status_code == 400
        assert 'error' in res.get_json()

    def test_blank_name_returns_400(self, client):
        c, _ = client
        res  = _post(c, {**MINIMAL_LAYOUT, 'name': '   '})
        assert res.status_code == 400

    def test_all_invalid_chars_name_returns_400(self, client):
        c, _ = client
        res  = _post(c, {**MINIMAL_LAYOUT, 'name': '!!@@##'})
        assert res.status_code == 400

    def test_no_body_returns_400(self, client):
        c, _ = client
        res  = c.post('/api/layout/save', data='', content_type='application/json')
        assert res.status_code == 400

    def test_malformed_json_returns_400(self, client):
        c, _ = client
        res  = c.post('/api/layout/save', data='not json', content_type='application/json')
        assert res.status_code == 400
