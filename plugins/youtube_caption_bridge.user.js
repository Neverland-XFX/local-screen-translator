// ==UserScript==
// @name         YouTube Caption Bridge
// @namespace    local-screen-translator
// @version      0.1
// @description  Send YouTube captions to a local translator on 127.0.0.1
// @match        https://www.youtube.com/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// ==/UserScript==

(function () {
  "use strict";

  const ENDPOINT = "http://127.0.0.1:8765/caption";
  let lastText = "";
  let observer = null;

  function normalize(text) {
    return text.replace(/\s+/g, " ").trim();
  }

  function extractCaptionText(container) {
    const segments = container.querySelectorAll(".ytp-caption-segment");
    if (!segments || segments.length === 0) {
      return "";
    }
    const raw = Array.from(segments)
      .map((node) => node.textContent || "")
      .join(" ");
    return normalize(raw);
  }

  function send(text) {
    if (!text || text === lastText) return;
    lastText = text;
    GM_xmlhttpRequest({
      method: "POST",
      url: ENDPOINT,
      data: text,
      headers: { "Content-Type": "text/plain" },
    });
  }

  function attachObserver() {
    const container = document.querySelector(".ytp-caption-window-container");
    if (!container) return false;

    if (observer) {
      observer.disconnect();
    }

    observer = new MutationObserver(() => {
      const text = extractCaptionText(container);
      send(text);
    });
    observer.observe(container, {
      childList: true,
      subtree: true,
      characterData: true,
    });

    return true;
  }

  setInterval(() => {
    if (!observer || !document.body.contains(document.querySelector(".ytp-caption-window-container"))) {
      attachObserver();
    }
  }, 1000);
})();
