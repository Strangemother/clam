import re

with open('python_readme_snippet.txt', 'r') as f:
    text = f.read()
    print("--- Python Installation ---")
    pip_match = re.search(r'pip install sqlite-ai', text)
    if pip_match:
        print(pip_match.group(0))
    
    print("\n--- Python Import/Load ---")
    py_match = re.search(r'```python\n(.*?import sqlite_ai.*?)\n```', text, re.DOTALL)
    if py_match:
        print(py_match.group(1))
    else:
        py_match = re.search(r'```python\n(.*?)\n```', text, re.DOTALL)
        if py_match:
            print(py_match.group(1))

with open('api_snippet.txt', 'r') as f:
    text = f.read()
    print("\n--- SQL Embedding Example ---")
    sql_match = re.search(r'```sql\n(.*?ai_embedding.*?)\n```', text, re.DOTALL)
    if sql_match:
        print(sql_match.group(1))
