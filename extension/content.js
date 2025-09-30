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

async function translateBatch(texts, source, target) {
  const endpoint = (await getEndpoint()).replace(/\/$/, "");
  const res = await fetch(`${endpoint}/translate_batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      items: texts.map((t) => ({ text: t, source: source || "auto", target: target || "vi" })),
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

function walkTextNodes(root) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
  const nodes = [];
  let n;
  while ((n = walker.nextNode())) {
    if (!n.nodeValue) continue;
    const text = n.nodeValue.trim();
    if (!text) continue;
    if (shouldSkip(n)) continue;
    if (n.parentElement && n.parentElement.dataset && n.parentElement.dataset.enviTranslated === '1') continue;
    nodes.push(n);
  }
  return nodes;
}

function shouldSkip(textNode) {
  // Skip in non-readable/unsafe containers
  const p = textNode.parentElement;
  if (!p) return true;
  const tag = p.tagName;
  const skipTags = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "CODE", "PRE", "TEXTAREA", "INPUT", "SELECT", "OPTION", "IFRAME", "SVG", "MATH"]);
  if (skipTags.has(tag)) return true;
  // Skip if content is likely code or pure numbers
  const val = textNode.nodeValue || "";
  if (/^\s*$/.test(val)) return true;
  return false;
}

function detectPageLang() {
  // 1) <html lang>
  const htmlLang = (document.documentElement.getAttribute('lang') || document.documentElement.getAttribute('xml:lang') || '').trim();
  if (htmlLang) return htmlLang;
  // 2) <meta http-equiv="content-language"> or name="language"/"lang"
  const metas = Array.from(document.getElementsByTagName('meta'));
  for (const m of metas) {
    const httpEquiv = (m.httpEquiv || '').toLowerCase();
    const name = (m.getAttribute('name') || '').toLowerCase();
    const content = (m.getAttribute('content') || '').trim();
    if (httpEquiv === 'content-language' && content) return content;
    if ((name === 'language' || name === 'lang' || name === 'og:locale') && content) return content;
  }
  // 3) navigator.language as a weak fallback
  return (navigator.language || 'auto');
}

async function translatePage(source, target) {
  const detected = detectPageLang();
  const useSource = (source && source.toLowerCase() !== 'auto') ? source : detected;
  const nodes = walkTextNodes(document.body);
  if (nodes.length === 0) return;

  // Chunk to avoid very large payloads and keep UI responsive
  const CHUNK_SIZE = 150;
  for (let i = 0; i < nodes.length; i += CHUNK_SIZE) {
    const chunk = nodes.slice(i, i + CHUNK_SIZE);
    const texts = chunk.map((n) => n.nodeValue);
    try {
      const out = await translateBatch(texts, useSource, target);
      chunk.forEach((n, idx) => {
        n.nodeValue = out[idx];
        if (n.parentElement) n.parentElement.dataset.enviTranslated = '1';
      });
    } catch (e) {
      console.warn('Batch translate failed', e);
      // Continue with next chunk
    }
  }
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "TRANSLATE_PAGE") {
    translatePage(msg.source, msg.target).then(() => sendResponse({ ok: true })).catch((e) => sendResponse({ ok: false, error: e.message }));
    return true; // async response
  }
});

// Auto-translate on load if enabled
(async function autoTranslateIfEnabled() {
  chrome.storage.sync.get({ autoTranslate: false }, async (items) => {
    if (!items.autoTranslate) return;
    const target = await getDefaultTarget();
    translatePage("auto", target).catch((e) => console.warn("Auto-translate failed", e));
  });
})();

// Observe DOM changes to translate dynamic content (when auto-translate is on)
(function observeDynamicContent() {
  let scheduled = false;
  let lastTarget = null;

  async function maybeTranslate() {
    if (scheduled) return;
    scheduled = true;
    setTimeout(async () => {
      try {
        const { autoTranslate } = await new Promise((resolve) => chrome.storage.sync.get({ autoTranslate: false }, resolve));
        if (!autoTranslate) {
          scheduled = false;
          return;
        }
        const target = await getDefaultTarget();
        lastTarget = target;
        await translatePage('auto', target);
      } catch (e) {
        console.warn('Dynamic translate failed', e);
      } finally {
        scheduled = false;
      }
    }, 600); // debounce
  }

  const observer = new MutationObserver((mutations) => {
    for (const m of mutations) {
      if (m.type === 'childList' && (m.addedNodes && m.addedNodes.length)) {
        maybeTranslate();
        break;
      }
      if (m.type === 'characterData') {
        maybeTranslate();
        break;
      }
    }
  });

  observer.observe(document.documentElement || document.body, {
    subtree: true,
    childList: true,
    characterData: true
  });
})();
