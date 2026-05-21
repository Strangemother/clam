"""
pyfuncs.py
──────────────────────────────────────────────────────────────────────────────
User-defined Python functions callable from the prompting graph via the
PyFunc node.

HOW IT WORKS
────────────
Any function defined here (or imported here at module level) is automatically
discovered by the /prompting/functions/ endpoint as long as it:

  1. Is not prefixed with an underscore.
  2. Has a return-type annotation of str  (→ str).
  3. All parameters have type annotations (str, int, float, or bool).

The frontend node reads the function list, creates one inbound pip per
parameter, and POSTs to /prompting/functions/call when triggered.

ADDING A FUNCTION
─────────────────

def my_func(param_a: str, param_b: str = 'default') -> str:
    \"\"\"One-line description shown in the UI tooltip.\"\"\"
    return param_a + param_b

That's it.  Restart the Flask server and click ⟳ in a PyFunc node to refresh.

EXAMPLES
────────
"""

import pathlib
import datetime

from simple_bulb import perform


def simple_bulb_perform(text: str) -> str:
    """Return the input unchanged."""
    return perform(text)
    # return text

# ── example functions ─────────────────────────────────────────────────────────

def echo(text: str) -> str:
    """Return the input unchanged."""
    return text


def uppercase(text: str) -> str:
    """Convert text to uppercase."""
    return text.upper()


def prepend_timestamp(text: str) -> str:
    """Prepend an ISO-8601 UTC timestamp to the text."""
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    return f'[{ts}] {text}'


def save_file(filename: str, content: str) -> str:
    """Save content to a file under the workspace output/ directory.
    Returns the absolute path on success."""
    out_dir = pathlib.Path(__file__).parent / 'output'
    out_dir.mkdir(exist_ok=True)
    # Sanitise filename — no path traversal
    safe_name = pathlib.Path(filename).name
    if not safe_name:
        return 'error: empty filename'
    dest = out_dir / safe_name
    dest.write_text(content, encoding='utf-8')
    return str(dest)


def join_lines(a: str, b: str) -> str:
    """Join two strings with a newline between them."""
    return f'{a}\n{b}'


def word_count(text: str) -> str:
    """Return the number of words in the text as a string."""
    return str(len(text.split()))
