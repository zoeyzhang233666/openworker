import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Markdown, OPEN_ARTIFACT_EVENT } from "./Markdown";

vi.mock("mermaid", () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn(async () => ({
      svg: '<svg data-testid="fake-svg"></svg>',
    })),
  },
}));

afterEach(cleanup);

// §34 (UX-016): [Title](artifact:path) renders as a chip that opens the artifact viewer via
// a window event; ordinary links keep the open-externally treatment.
describe("Markdown artifact links", () => {
  it("renders an artifact: link as a chip and dispatches the open event with the path", () => {
    const seen: string[] = [];
    const listener = (e: Event) => seen.push((e as CustomEvent).detail.path);
    window.addEventListener(OPEN_ARTIFACT_EVENT, listener);

    render(<Markdown text="Done — [Semiconductor dashboard](artifact:reports/semi.html)" />);
    const chip = screen.getByTestId("artifact-chip");
    expect(chip.textContent).toContain("Semiconductor dashboard");
    expect(chip.textContent).toContain("semi.html"); // filename shown under the title
    fireEvent.click(chip);
    expect(seen).toEqual(["reports/semi.html"]);

    window.removeEventListener(OPEN_ARTIFACT_EVENT, listener);
  });

  it("ordinary links stay external and never become chips", () => {
    const { container } = render(<Markdown text="see [the docs](https://example.com)" />);
    expect(screen.queryByTestId("artifact-chip")).toBeNull();
    const a = container.querySelector("a")!;
    expect(a.getAttribute("target")).toBe("_blank");
    expect(a.getAttribute("href")).toBe("https://example.com");
  });

  it("chip title falls back to the filename when the link text is empty", () => {
    vi.spyOn(window, "dispatchEvent");
    render(<Markdown text="[](artifact:out/report.pdf)" />);
    expect(screen.getByTestId("artifact-chip").textContent).toContain("report.pdf");
  });

  // react-markdown percent-encodes non-ASCII in hrefs; the chip must decode so
  // readArtifact looks up the real workspace-relative filename.
  it("decodes percent-encoded non-ASCII artifact paths before opening", () => {
    const seen: string[] = [];
    const listener = (e: Event) => seen.push((e as CustomEvent).detail.path);
    window.addEventListener(OPEN_ARTIFACT_EVENT, listener);

    render(<Markdown text="[丙烯产业链研究报告](artifact:丙烯产业链研究报告.md)" />);
    fireEvent.click(screen.getByTestId("artifact-chip"));
    expect(seen).toEqual(["丙烯产业链研究报告.md"]);

    window.removeEventListener(OPEN_ARTIFACT_EVENT, listener);
  });

  it("renders relative workspace .md links as chips (not blue external anchors)", () => {
    const seen: string[] = [];
    const listener = (e: Event) => seen.push((e as CustomEvent).detail.path);
    window.addEventListener(OPEN_ARTIFACT_EVENT, listener);

    const { container } = render(<Markdown text="见 [产业链分析](产业链分析.md)" />);
    expect(container.querySelector("a")).toBeNull();
    fireEvent.click(screen.getByTestId("artifact-chip"));
    expect(seen).toEqual(["产业链分析.md"]);

    window.removeEventListener(OPEN_ARTIFACT_EVENT, listener);
  });
});

describe("Markdown mermaid fence", () => {
  it("renders MermaidBlock for ```mermaid when enabled", async () => {
    const text = "见下图\n\n```mermaid\ngraph TD; A-->B\n```\n";
    render(<Markdown text={text} />);
    await waitFor(() => expect(screen.getByTestId("mermaid-block")).toBeTruthy());
  });

  it("keeps ordinary code as pre/code", () => {
    render(<Markdown text={"```js\nconsole.log(1)\n```"} />);
    expect(screen.queryByTestId("mermaid-block")).toBeNull();
    expect(document.querySelector("pre code")?.textContent).toContain("console.log");
  });

  it("skips MermaidBlock when renderMermaid is false", () => {
    const text = "```mermaid\ngraph TD; A-->B\n```";
    render(<Markdown text={text} renderMermaid={false} />);
    expect(screen.queryByTestId("mermaid-block")).toBeNull();
    expect(document.querySelector("pre code")?.className || "").toMatch(/language-mermaid/);
  });

  // Parent re-renders (scroll follow, inbox poll, etc.) must not tear down MermaidBlock
  // or mermaid.render runs again → svg cleared → scrollHeight collapses → page jitter.
  it("does not re-render mermaid when Markdown rerenders with the same text", async () => {
    const mermaid = await import("mermaid");
    const renderFn = mermaid.default.render as ReturnType<typeof vi.fn>;
    const text = "```mermaid\ngraph TD; A-->B\n```";
    const { rerender } = render(<Markdown text={text} />);
    await waitFor(() => expect(screen.getByTestId("mermaid-diagram")).toBeTruthy());
    const callsAfterFirst = renderFn.mock.calls.length;
    expect(callsAfterFirst).toBeGreaterThanOrEqual(1);

    rerender(<Markdown text={text} />);
    rerender(<Markdown text={text} />);
    rerender(<Markdown text={text} />);
    await new Promise((r) => setTimeout(r, 80));

    expect(renderFn.mock.calls.length).toBe(callsAfterFirst);
    expect(screen.getByTestId("mermaid-diagram")).toBeTruthy();
    expect(screen.queryByText(/正在渲染|Rendering/i)).toBeNull();
  });
});
