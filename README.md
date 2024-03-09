# Running

## Installation Instructions

### Using PDM

```bash
pdm install
source .venv/bin/activate
```

### Using pip

```bash

python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Running the Server

```bash
cd doqfy
python manage.py migrate
python manage.py runserver
```

# Endpoints

- URL shortener -> /shorten
- Share snippets -> /shareme
