// Create context menu for translating selected text
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "translate-selection",
    title: "Translate selection via ENVI API",
    contexts: ["selection"]
  });
});

async function callApi(text, source, target) {
  const body = {
    text,
    source: source || "auto",
    target: target || (await getDefaultTarget()),
    preserve_format: true,
    max_chars: 4500,
    retries: 3,
    retry_backoff_sec: 1.0
  };
  const endpoint = (await getEndpoint()).replace(/\/$/, "");
  const res = await fetch(`${endpoint}/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(`API error ${res.status}: ${t}`);
  }
  const data = await res.json();
  return data.translated;
}

async function getEndpoint() {
  return new Promise((resolve) => {
    chrome.storage.sync.get({ apiEndpoint: "http://127.0.0.1:8000" }, (items) => {
      resolve(items.apiEndpoint);
    });
  });
}

async function getDefaultTarget() {
  return new Promise((resolve) => {
    chrome.storage.sync.get({ defaultTarget: "vi" }, (items) => {
      resolve(items.defaultTarget || "vi");
    });
  });
}

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "translate-selection" && info.selectionText) {
    try {
      const translated = await callApi(info.selectionText, "auto", await getDefaultTarget());
      chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: (text) => alert(text),
        args: [translated]
      });
    } catch (e) {
      chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: (msg) => alert(`Translation failed: ${msg}`),
        args: [e.message]
      });
    }
  }
});
