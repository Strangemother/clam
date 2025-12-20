# clam backbone

Run a central service for all bots and services, allowing easier discovery of units, and cross communication of bots

```bash
> clam backbone
# Loading config config.py
# Loaded local config True
Socket running at http://127.0.0.1:5000
```

The app will load more than once if the flask debug is `True`:

```bash
> clam backbone
# Loading config config.py
# Loaded local config True
Starting backbone service on 127.0.0.1:5000
 * Serving Flask app 'clam.backbone'
 * Debug mode: on

Socket running at http://127.0.0.1:5000
# Loading config config.py
# Loaded local config True
Starting backbone service on 127.0.0.1:5000
```