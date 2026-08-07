/** HTML artifact preview hardening for RightRail srcDoc (D-078). */

/** True when a script src points at an absolute http(s) URL (protocol-relative included). */
export function isExternalScriptSrc(src: string): boolean {
  const s = (src || "").trim();
  if (!s) return false;
  if (/^https?:\/\//i.test(s)) return true;
  if (s.startsWith("//")) return true;
  return false;
}

/**
 * Historically stripped external scripts (D-077). D-078 keeps CDN / https scripts so
 * interactive charts and public APIs work; this is now a no-op pass-through.
 */
export function stripExternalScripts(html: string): string {
  return html || "";
}

const GUARD_SCRIPT = `<script data-chemclaw-preview-guard="1">
(function () {
  if (window.__chemclawPreviewGuard) return;
  window.__chemclawPreviewGuard = true;
  function methodOf(init, fallback) {
    try {
      if (init && init.method) return String(init.method).toUpperCase();
    } catch (e) {}
    return fallback || "GET";
  }
  var origFetch = window.fetch;
  if (typeof origFetch === "function") {
    window.fetch = function (input, init) {
      var m = methodOf(init, "GET");
      if (m !== "GET" && m !== "HEAD") {
        return Promise.reject(new Error("ChemClaw preview: only read-only GET is allowed"));
      }
      return origFetch.apply(this, arguments);
    };
  }
  var XO = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method) {
    var m = String(method || "GET").toUpperCase();
    if (m !== "GET" && m !== "HEAD") {
      throw new Error("ChemClaw preview: only read-only GET is allowed");
    }
    return XO.apply(this, arguments);
  };
})();
</script>`;

// Allow https CDN scripts (Chart.js etc.) + inline; still block form POST of report content.
const CSP_META =
  `<meta http-equiv="Content-Security-Policy" content="script-src 'unsafe-inline' 'unsafe-eval' https: blob: data:; object-src 'none'; base-uri 'none'; form-action 'none';">`;

/** Insert guard + CSP as early as practical without breaking existing markup. */
export function injectPreviewGuards(html: string): string {
  const input = html || "";
  if (/data-chemclaw-preview-guard\s*=\s*["']?1["']?/i.test(input)) {
    return input;
  }
  const headOpen = /<head\b[^>]*>/i.exec(input);
  if (headOpen) {
    const i = headOpen.index + headOpen[0].length;
    return input.slice(0, i) + CSP_META + GUARD_SCRIPT + input.slice(i);
  }
  const htmlOpen = /<html\b[^>]*>/i.exec(input);
  if (htmlOpen) {
    const i = htmlOpen.index + htmlOpen[0].length;
    return (
      input.slice(0, i) +
      "<head>" +
      CSP_META +
      GUARD_SCRIPT +
      "</head>" +
      input.slice(i)
    );
  }
  return "<!DOCTYPE html><html><head>" + CSP_META + GUARD_SCRIPT + "</head><body>" + input + "</body></html>";
}

/** Full pipeline for RightRail srcDoc. */
export function prepareHtmlPreview(html: string): string {
  return injectPreviewGuards(stripExternalScripts(html));
}
