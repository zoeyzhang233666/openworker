import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FolderGate } from "./FolderGate";
import { LocaleProvider } from "../i18n";

vi.mock("../api", () => ({
  getRecentWorkspaces: vi.fn(async () => []),
  openWorkspace: vi.fn(async () => ({ ok: true, path: "/x", git_branch: null })),
}));

vi.mock("../tauri", () => ({
  chooseFolder: vi.fn(async () => null),
}));

afterEach(() => cleanup());

function renderGate(onCancel?: () => void) {
  return render(
    <LocaleProvider>
      <FolderGate onChoose={() => {}} onCancel={onCancel} />
    </LocaleProvider>,
  );
}

describe("FolderGate D-082 close affordance", () => {
  it("shows 关闭 when onCancel is provided (even with no workspace yet)", () => {
    const onCancel = vi.fn();
    renderGate(onCancel);
    const btn = screen.getByRole("button", { name: /关闭|Close/i });
    fireEvent.click(btn);
    expect(onCancel).toHaveBeenCalled();
  });

  it("hides the close row when onCancel is omitted", () => {
    renderGate(undefined);
    expect(screen.queryByRole("button", { name: /关闭|Close/i })).toBeNull();
  });
});
