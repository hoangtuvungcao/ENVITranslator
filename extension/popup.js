async function getEndpoint() {
  return new Promise((resolve) => {
    chrome.storage.sync.get({ apiEndpoint: "http://127.0.0.1:8000" }, (items) => {
      resolve(items.apiEndpoint);
    });
  });
}

async function fetchLanguages() {
  const endpoint = (await getEndpoint()).replace(/\/$/, "");
  const res = await fetch(`${endpoint}/languages?as_dict=true`);
  if (!res.ok) throw new Error(`Lang API error ${res.status}`);
  return res.json();
}

async function translate(text, source, target) {
  const endpoint = (await getEndpoint()).replace(/\/$/, "");
  const res = await fetch(`${endpoint}/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      source: source || "auto",
      target: target || "vi",
      preserve_format: true,
      max_chars: 4500,
      retries: 3,
      retry_backoff_sec: 1.0
    })
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  const data = await res.json();
  return data.translated;
}

window.addEventListener("DOMContentLoaded", () => {
  const sourceText = document.getElementById("sourceText");
  const targetText = document.getElementById("targetText");
  const text = document.getElementById("text");
  const btnText = document.getElementById("translateTextBtn");
  const result = document.getElementById("result");

  (async () => {
    try {
      const langs = await fetchLanguages();
      // Build options for text
      sourceText.innerHTML = '';
      const autoOpt = document.createElement('option');
      autoOpt.value = 'auto';
      autoOpt.textContent = 'auto';
      sourceText.appendChild(autoOpt);
      Object.entries(langs).forEach(([name, code]) => {
        const opt = document.createElement('option');
        opt.value = code;
        opt.textContent = `${name} (${code})`;
        sourceText.appendChild(opt);
      });

      targetText.innerHTML = '';
      Object.entries(langs).forEach(([name, code]) => {
        const opt = document.createElement('option');
        opt.value = code;
        opt.textContent = `${name} (${code})`;
        targetText.appendChild(opt);
      });

      // Restore saved prefs
      chrome.storage.sync.get({ defaultTarget: 'vi' }, (items) => {
        sourceText.value = 'auto';
        targetText.value = items.defaultTarget || 'vi';
      });
    } catch (e) {
      // Fallback language set if API fails
      const fallback = {
        "English": "en",
        "Vietnamese": "vi",
        "Japanese": "ja",
        "French": "fr",
        "German": "de",
        "Spanish": "es",
        "Chinese (Simplified)": "zh-CN",
        "Chinese (Traditional)": "zh-TW",
        "Korean": "ko",
        "Portuguese": "pt",
        "Italian": "it",
        "Indonesian": "id",
        "Thai": "th",
        "Russian": "ru"
      };
      sourceText.innerHTML = '';
      const autoOpt = document.createElement('option');
      autoOpt.value = 'auto';
      autoOpt.textContent = 'auto';
      sourceText.appendChild(autoOpt);
      Object.entries(fallback).forEach(([name, code]) => {
        const opt = document.createElement('option');
        opt.value = code;
        opt.textContent = `${name} (${code})`;
        sourceText.appendChild(opt);
      });
      targetText.innerHTML = '';
      Object.entries(fallback).forEach(([name, code]) => {
        const opt = document.createElement('option');
        opt.value = code;
        opt.textContent = `${name} (${code})`;
        targetText.appendChild(opt);
      });
      chrome.storage.sync.get({ defaultTarget: 'vi' }, (items) => {
        sourceText.value = 'auto';
        targetText.value = items.defaultTarget || 'vi';
      });
      // Also show a small hint
      result.textContent = `Using fallback languages (API error: ${e.message})`;
    }
  })();

  btnText.addEventListener("click", async () => {
    btnText.disabled = true;
    result.textContent = "Translating...";
    try {
      const out = await translate(text.value, sourceText.value.trim(), targetText.value.trim());
      result.textContent = out;
      // Save chosen target as default
      chrome.storage.sync.set({ defaultTarget: targetText.value.trim() });
    } catch (e) {
    } finally {
      btnText.disabled = false;
    }
  });
});
