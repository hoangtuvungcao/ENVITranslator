# English ↔ Vietnamese Translator (Python)

A minimal Python module and CLI to translate between English and Vietnamese using Google (via `deep-translator`).

## Features
- **EN → VI** and **VI → EN** translation
- **Translate text from CLI** or **translate files**
- **Library API** for use in your own Python code
 - **Accuracy helpers**: formatting preservation, safe chunking, retry/backoff

## Installation
```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

## CLI Usage
Run with module entry point:
```bash
python -m envi_translator --help
```

Examples:
- English to Vietnamese (text):
```bash
python -m envi_translator en2vi -t "Hello, how are you?"
```
- Vietnamese to English (text):
```bash
python -m envi_translator vi2en -t "Chào bạn, bạn khỏe không?"
```
- Translate a file (auto-detect → Vietnamese):
```bash
python -m envi_translator translate -i input.txt -o output.txt --target vi
```

### Accuracy and robustness options
- `--preserve-format` / `--no-preserve-format` (default: preserve on)
  - Keep line breaks and spacing to maintain context and layout.
- `--max-chars <int>` (default: 4500)
  - Safe chunk size to avoid provider limits for long texts.
- `--retries <int>` (default: 3) and `--retry-backoff <float>` (default: 1.0)
  - Automatic retries per chunk with exponential backoff.

Example with options:
```bash
python -m envi_translator en2vi -t "Complex, long text..." \
  --preserve-format --max-chars 4000 --retries 5 --retry-backoff 1.5
```

## Library Usage
```python
from envi_translator.translator import ENVITranslator

# Quick helpers
print(ENVITranslator.en_to_vi("Good morning"))
print(ENVITranslator.vi_to_en("Chúc buổi sáng"))

# Custom source/target
tr = ENVITranslator(source="auto", target="vi")
print(tr.translate_text(
    "Weather is nice today",
    preserve_format=True,
    max_chars=4500,
    retries=3,
    retry_backoff_sec=1.0,
))
```

## Notes
- Requires internet access (uses Google translate backend via `deep-translator`).
- If Google rate-limits, retry after a short delay.
 - For best fidelity: enable `--preserve-format`, keep sentences clear, and avoid excessive slang.

---

# REST API Server
A FastAPI server is included at `main.py`.

## Run the API
```bash
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Endpoints
- `GET /health` → health check
- `GET /languages?as_dict=true` → supported languages
- `POST /translate` → body:
```json
{
  "text": "Hello",
  "source": "auto",
  "target": "vi",
  "preserve_format": true,
  "max_chars": 4500,
  "retries": 3,
  "retry_backoff_sec": 1.0
}
```

---

# Chrome Extension (MV3)
Files under `extension/` provide a Chrome extension that calls the local API.

## Load the extension
1. Open Chrome → `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" and select the `extension/` folder
4. (Optional) Open "Options" and set API endpoint (default `http://127.0.0.1:8000`)

## Usage
- Select text on any webpage → right-click → "Translate selection via ENVI API" → popup alert shows translation
- Click the extension icon to open the popup, type text, set source/target, and translate

Note: The extension manifest references `icon.png` for icons. You can add any PNG to `extension/icon.png` with sizes 16/48/128 or remove the icons section in `manifest.json` if you prefer.
