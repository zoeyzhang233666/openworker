import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import mermaid from "mermaid";
import { MermaidBlock } from "./MermaidBlock";

const renderMock = vi.fn(async (_id: string, _src: string) => ({
  svg: '<svg data-testid="fake-svg" xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200"><rect width="400" height="200" fill="#ddd"/></svg>',
}));

vi.mock("mermaid", () => ({
  default: {
    initialize: vi.fn(),
    render: (...args: unknown[]) => renderMock(...(args as [string, string])),
  },
}));

afterEach(() => {
  cleanup();
  renderMock.mockClear();
});

describe("MermaidBlock", () => {
  it("initializes mermaid with the neo theme", async () => {
    render(<MermaidBlock source={"graph TD; A-->B"} />);
    await waitFor(() => expect(screen.getByTestId("mermaid-diagram")).toBeTruthy());
    expect(mermaid.initialize).toHaveBeenCalledWith(
      expect.objectContaining({ theme: "neo" }),
    );
  });

  it("renders svg for valid source once", async () => {
    render(<MermaidBlock source={"graph TD; A-->B"} />);
    await waitFor(() => expect(screen.getByTestId("mermaid-diagram")).toBeTruthy());
    expect(renderMock).toHaveBeenCalledTimes(1);
  });

  it("toggles to source and back without re-render", async () => {
    render(<MermaidBlock source={"graph TD; A-->B"} />);
    await waitFor(() => screen.getByTestId("mermaid-diagram"));
    fireEvent.click(screen.getByRole("button", { name: /源码|Source/i }));
    expect(screen.getByTestId("mermaid-source").textContent).toContain("graph TD");
    fireEvent.click(screen.getByRole("button", { name: /图形|Diagram/i }));
    expect(screen.getByTestId("mermaid-diagram")).toBeTruthy();
    expect(renderMock).toHaveBeenCalledTimes(1);
  });

  it("shows error and source on render failure", async () => {
    renderMock.mockRejectedValueOnce(new Error("parse"));
    render(<MermaidBlock source={"not mermaid"} />);
    await waitFor(() => expect(screen.getByTestId("mermaid-error")).toBeTruthy());
    expect(screen.getByTestId("mermaid-source")).toBeTruthy();
  });

  it("rejects oversized source without calling mermaid.render", async () => {
    const huge = "x".repeat(50_001);
    render(<MermaidBlock source={huge} />);
    await waitFor(() => expect(screen.getByTestId("mermaid-error")).toBeTruthy());
    expect(renderMock).not.toHaveBeenCalled();
  });

  it("locks min-height on the diagram container, not a fixed height", async () => {
    const offsetSpy = vi
      .spyOn(HTMLElement.prototype, "offsetHeight", "get")
      .mockImplementation(function (this: HTMLElement) {
        return this.getAttribute("data-testid") === "mermaid-diagram" ? 240 : 0;
      });

    render(<MermaidBlock source={"graph TD; A-->B"} />);
    const diagram = await screen.findByTestId("mermaid-diagram");
    // minHeight lock avoids nested overflow-y scroll traps from fixed height.
    await waitFor(() => expect(diagram.style.minHeight).toBe("240px"));
    expect(diagram.style.height).toBe("");
    expect(screen.getByTestId("mermaid-block").style.height).toBe("");

    offsetSpy.mockRestore();
  });

  it("clears diagram height lock when source becomes oversized", async () => {
    const offsetSpy = vi
      .spyOn(HTMLElement.prototype, "offsetHeight", "get")
      .mockImplementation(function (this: HTMLElement) {
        return this.getAttribute("data-testid") === "mermaid-diagram" ? 240 : 0;
      });

    const { rerender } = render(<MermaidBlock source={"graph TD; A-->B"} />);
    const diagram = await screen.findByTestId("mermaid-diagram");
    await waitFor(() => expect(diagram.style.minHeight).toBe("240px"));

    rerender(<MermaidBlock source={"x".repeat(50_001)} />);
    await waitFor(() => expect(screen.getByTestId("mermaid-error")).toBeTruthy());
    expect(screen.queryByTestId("mermaid-diagram")).toBeNull();
    expect(screen.getByTestId("mermaid-block").style.height).toBe("");

    offsetSpy.mockRestore();
  });

  it("opens lightbox from fullscreen button", async () => {
    render(<MermaidBlock source={"graph TD; A-->B"} />);
    await waitFor(() => screen.getByTestId("mermaid-diagram"));
    fireEvent.click(screen.getByRole("button", { name: /全屏|Fullscreen/i }));
    expect(screen.getByTestId("mermaid-lightbox")).toBeTruthy();
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByTestId("mermaid-lightbox")).toBeNull());
  });

  it("keeps toolbar mounted without is-error so CSS can hide chrome until hover/focus", async () => {
    render(<MermaidBlock source={"graph TD; A-->B"} />);
    const block = await screen.findByTestId("mermaid-block");
    await waitFor(() => expect(screen.getByTestId("mermaid-diagram")).toBeTruthy());
    expect(block.className).toBe("mermaid-block");
    expect(block.classList.contains("is-error")).toBe(false);
    // Toolbar stays in the tree (visibility:hidden via CSS) to reserve height.
    expect(block.querySelector(".mermaid-block-toolbar")).toBeTruthy();
    expect(screen.getByRole("button", { name: /全屏|Fullscreen/i })).toBeTruthy();
  });

  it("adds is-error when render fails so chrome stays visible without hover", async () => {
    renderMock.mockRejectedValueOnce(new Error("parse"));
    render(<MermaidBlock source={"not mermaid"} />);
    const block = await screen.findByTestId("mermaid-block");
    await waitFor(() => expect(screen.getByTestId("mermaid-error")).toBeTruthy());
    expect(block.classList.contains("is-error")).toBe(true);
    expect(screen.getByTestId("mermaid-source")).toBeTruthy();
  });

  it("adds is-error when source is oversized", async () => {
    render(<MermaidBlock source={"x".repeat(50_001)} />);
    const block = await screen.findByTestId("mermaid-block");
    await waitFor(() => expect(screen.getByTestId("mermaid-error")).toBeTruthy());
    expect(block.classList.contains("is-error")).toBe(true);
  });

  it("closes lightbox when clicking backdrop mask", async () => {
    render(<MermaidBlock source={"graph TD; A-->B"} />);
    await waitFor(() => screen.getByTestId("mermaid-diagram"));
    fireEvent.click(screen.getByRole("button", { name: /全屏|Fullscreen/i }));
    const lightbox = screen.getByTestId("mermaid-lightbox");
    const viewport = lightbox.querySelector(".mermaid-lightbox-viewport");
    expect(viewport).toBeTruthy();
    fireEvent.click(viewport!);
    await waitFor(() => expect(screen.queryByTestId("mermaid-lightbox")).toBeNull());
  });

  it("fullscreen stage sizes SVG by CSS width/height (vector), not a tiny capped bitmap", async () => {
    render(<MermaidBlock source={"graph TD; A-->B"} />);
    await waitFor(() => screen.getByTestId("mermaid-diagram"));
    fireEvent.click(screen.getByRole("button", { name: /全屏|Fullscreen/i }));
    const stage = await screen.findByTestId("mermaid-lightbox-stage");
    await waitFor(() => {
      const w = parseFloat(stage.style.width || "0");
      expect(w).toBeGreaterThan(100);
    });
    expect(stage.style.height).toMatch(/^\d+px$/);
    const svg = stage.querySelector("svg");
    expect(svg).toBeTruthy();
    expect(svg!.hasAttribute("viewBox") || svg!.getAttribute("viewBox")).toBeTruthy();
  });
});
