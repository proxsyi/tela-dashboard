(function () {
  'use strict';

  function decodeHtmlEntities(text) {
    try {
      const ta = document.createElement('textarea');
      ta.innerHTML = text;
      return ta.value;
    } catch (_) {
      return text
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'");
    }
  }

  function extractJsonFromText(text) {
    if (!text || typeof text !== 'string') return null;

    // Strategy 1: raw JSON object at start of text
    const trimmed = text.trim();
    if (trimmed.startsWith('{')) {
      try { return JSON.parse(trimmed); } catch (_) {}
    }

    // Strategy 2: JSON inside ```json fences
    const fenceMatch = trimmed.match(/```json\s*([\s\S]*?)```/i);
    if (fenceMatch) {
      try { return JSON.parse(fenceMatch[1].trim()); } catch (_) {}
    }

    // Strategy 3: generic ``` fences
    const genericFence = trimmed.match(/```\s*([\s\S]*?)```/);
    if (genericFence) {
      const inner = genericFence[1].trim();
      if (inner.startsWith('{')) {
        try { return JSON.parse(inner); } catch (_) {}
      }
    }

    // Strategy 4: first { ... } block found anywhere
    const objStart = text.indexOf('{');
    if (objStart !== -1) {
      // walk forward to find balanced closing brace
      let depth = 0;
      for (let i = objStart; i < text.length; i++) {
        if (text[i] === '{') depth++;
        else if (text[i] === '}') {
          depth--;
          if (depth === 0) {
            try { return JSON.parse(text.slice(objStart, i + 1)); } catch (_) { break; }
          }
        }
      }
    }

    // Strategy 5: HTML entity decode then retry
    const decoded = decodeHtmlEntities(text);
    if (decoded !== text) {
      return extractJsonFromText(decoded);
    }

    return null;
  }

  async function loadJsonConfig(url) {
    try {
      const res = await fetch(url, { mode: 'cors' });
      if (!res.ok) {
        console.warn('[TelaSource] loadJsonConfig: HTTP', res.status, url);
        return null;
      }
      const text = await res.text();
      const obj = extractJsonFromText(text);
      if (obj) {
        console.log('[TelaSource] loadJsonConfig: parsed config from', url);
      } else {
        console.warn('[TelaSource] loadJsonConfig: could not parse JSON from', url);
      }
      return obj;
    } catch (err) {
      if (err instanceof TypeError && err.message.toLowerCase().includes('fetch')) {
        console.warn('[TelaSource] loadJsonConfig: CORS/network blocked for', url);
      } else {
        console.warn('[TelaSource] loadJsonConfig error:', err.message);
      }
      return null;
    }
  }

  async function loadNotionPublicConfig(url) {
    try {
      const res = await fetch(url, { mode: 'cors' });
      if (!res.ok) {
        console.warn('[TelaSource] loadNotionPublicConfig: HTTP', res.status, url);
        return null;
      }
      const text = await res.text();
      const obj = extractJsonFromText(text);
      if (obj) {
        console.log('[TelaSource] loadNotionPublicConfig: parsed config from Notion page', url);
      } else {
        console.warn('[TelaSource] loadNotionPublicConfig: no parseable JSON found in Notion page', url);
      }
      return obj;
    } catch (err) {
      if (err instanceof TypeError) {
        console.warn('[TelaSource] loadNotionPublicConfig: CORS blocked fetching Notion page', url,
          '— this is expected; use a public JSON URL instead.');
      } else {
        console.warn('[TelaSource] loadNotionPublicConfig error:', err.message);
      }
      return null;
    }
  }

  async function loadRemoteConfig() {
    const params = new URLSearchParams(window.location.search);
    const jsonUrl = params.get('config');
    const notionUrl = params.get('notionSource');

    if (jsonUrl) {
      console.log('[TelaSource] Trying JSON config from query param:', jsonUrl);
      const cfg = await loadJsonConfig(jsonUrl);
      if (cfg) return cfg;
    }

    if (notionUrl) {
      console.log('[TelaSource] Trying Notion public page from query param:', notionUrl);
      const cfg = await loadNotionPublicConfig(notionUrl);
      if (cfg) return cfg;
    }

    return null;
  }

  window.TelaSource = {
    loadRemoteConfig,
    loadJsonConfig,
    loadNotionPublicConfig,
    extractJsonFromText,
  };
})();
