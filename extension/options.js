async function getEndpoint() {
  return new Promise((resolve) => {
    chrome.storage.sync.get({ apiEndpoint: 'http://127.0.0.1:8000' }, (items) => {
      resolve(items.apiEndpoint);
    });
  });
}

async function fetchLanguages() {
  const endpoint = (await getEndpoint()).replace(/\/$/, '');
  const res = await fetch(`${endpoint}/languages?as_dict=true`);
  if (!res.ok) throw new Error(`Lang API error ${res.status}`);
  return res.json();
}

function save() {
  const endpoint = document.getElementById('apiEndpoint').value.trim();
  const defaultTarget = document.getElementById('defaultTarget').value.trim();
  const autoTranslate = document.getElementById('autoTranslate').checked;
  chrome.storage.sync.set({
    apiEndpoint: endpoint || 'http://127.0.0.1:8000',
    defaultTarget: defaultTarget || 'vi',
    autoTranslate
  }, () => {
    const s = document.getElementById('status');
    s.textContent = 'Saved!';
    setTimeout(() => (s.textContent = ''), 1500);
  });
}

async function restore() {
  // Restore endpoint and preferences
  chrome.storage.sync.get({ apiEndpoint: 'http://127.0.0.1:8000', defaultTarget: 'vi', autoTranslate: false }, async (items) => {
    document.getElementById('apiEndpoint').value = items.apiEndpoint;
    try {
      const langs = await fetchLanguages();
      const select = document.getElementById('defaultTarget');
      select.innerHTML = '';
      Object.entries(langs).forEach(([name, code]) => {
        const opt = document.createElement('option');
        opt.value = code;
        opt.textContent = `${name} (${code})`;
        select.appendChild(opt);
      });
      select.value = items.defaultTarget || 'vi';
    } catch (e) {
      const s = document.getElementById('status');
      s.textContent = `Failed to load languages: ${e.message}`;
    }
    document.getElementById('autoTranslate').checked = !!items.autoTranslate;
  });
}

document.addEventListener('DOMContentLoaded', restore);

document.getElementById('saveBtn').addEventListener('click', save);
