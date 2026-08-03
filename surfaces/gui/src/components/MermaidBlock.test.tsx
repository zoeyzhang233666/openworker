import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MermaidBlock } from "./MermaidBlock";

const renderMock = vi.fn(async (_id: string, _src: string) => ({
  svg: '<svg data-testid="fake-svg"></svg>',
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

  it("locks height on the diagram container, not the outer block", async () => {
    const offsetSpy = vi
      .spyOn(HTMLElement.prototype, "offsetHeight", "get")
      .mockImplementation(function (this: HTMLElement) {
        return this.getAttribute("data-testid") === "mermaid-diagram" ? 240 : 0;
      });

    render(<MermaidBlock source={"graph TD; A-->B"} />);
    const diagram = await screen.findByTestId("mermaid-diagram");
    await waitFor(() => expect(diagram.style.height).toBe("240px"));
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
    await waitFor(() => expect(diagram.style.height).toBe("240px"));

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
});
