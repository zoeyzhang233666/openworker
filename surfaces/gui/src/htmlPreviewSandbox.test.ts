import { describe, expect, it } from "vitest";
import {
  injectPreviewGuards,
  isExternalScriptSrc,
  prepareHtmlPreview,
  stripExternalScripts,
} from "./htmlPreviewSandbox";

describe("isExternalScriptSrc", () => {
  it("flags http(s) and protocol-relative", () => {
    expect(isExternalScriptSrc("https://cdn.example/a.js")).toBe(true);
    expect(isExternalScriptSrc("http://evil/x.js")).toBe(true);
    expect(isExternalScriptSrc("//cdn.example/a.js")).toBe(true);
  });

  it("allows relative, blob, data, empty", () => {
    expect(isExternalScriptSrc("./app.js")).toBe(false);
    expect(isExternalScriptSrc("/local.js")).toBe(false);
    expect(isExternalScriptSrc("blob:abc")).toBe(false);
    expect(isExternalScriptSrc("data:text/javascript,1")).toBe(false);
    expect(isExternalScriptSrc("")).toBe(false);
  });
});

describe("stripExternalScripts", () => {
  it("D-078: keeps external CDN scripts (pass-through)", () => {
    const html = `
<html><body>
<script src="https://cdn.example/lib.js"></script>
<script>window.ok = 1</script>
<script src="//cdn.example/x.js"></script>
<script src="./local.js"></script>
</body></html>`;
    const out = stripExternalScripts(html);
    expect(out).toContain("https://cdn.example/lib.js");
    expect(out).toContain("//cdn.example/x.js");
    expect(out).toContain("window.ok = 1");
    expect(out).toContain('src="./local.js"');
    expect(out).not.toContain("chemclaw: stripped external script");
  });
});

describe("injectPreviewGuards", () => {
  it("injects CSP (https scripts allowed) and GET-only guard into head", () => {
    const out = injectPreviewGuards("<html><head><title>t</title></head><body>hi</body></html>");
    expect(out).toContain("Content-Security-Policy");
    expect(out).toContain("script-src 'unsafe-inline'");
    expect(out).toContain("https:");
    expect(out).toContain("form-action 'none'");
    expect(out).toContain("only read-only GET is allowed");
    expect(out).toContain('data-chemclaw-preview-guard="1"');
  });

  it("is idempotent", () => {
    const once = injectPreviewGuards("<html><head></head><body></body></html>");
    const twice = injectPreviewGuards(once);
    expect(twice.match(/data-chemclaw-preview-guard/g)?.length).toBe(1);
  });
});

describe("prepareHtmlPreview", () => {
  it("keeps external scripts and injects GET-only guard", () => {
    const out = prepareHtmlPreview(
      '<html><head></head><body><script src="https://x/y.js"></script><script>1</script></body></html>',
    );
    expect(out).toContain("https://x/y.js");
    expect(out).toContain("data-chemclaw-preview-guard");
    expect(out).toContain("<script>1</script>");
    expect(out).toContain("only read-only GET is allowed");
  });
});
