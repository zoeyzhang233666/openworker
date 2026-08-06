import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, act } from "@testing-library/react";
import { LocaleProvider } from "./i18n";
import { FirstTokenWaitLabel } from "./FirstTokenWaitLabel";
import { interfaceMessagesZh } from "./interfaceMessages";
import {
  FIRST_TOKEN_WAIT_ROTATE_MS,
  FIRST_TOKEN_WAIT_ROTATION_KEYS,
} from "./firstTokenWaitCopy";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  localStorage.clear();
});

beforeEach(() => {
  vi.useFakeTimers();
  localStorage.clear();
});

function zh(key: string): string {
  return interfaceMessagesZh[key as keyof typeof interfaceMessagesZh] ?? key;
}

function renderWait(active: boolean) {
  return render(
    <LocaleProvider>
      <FirstTokenWaitLabel active={active} />
    </LocaleProvider>,
  );
}

describe("FirstTokenWaitLabel", () => {
  it("renders nothing when inactive", () => {
    const { container } = renderWait(false);
    expect(container.querySelector("[data-testid=first-token-wait]")).toBeNull();
  });

  it("rotates early→late every 3s and wraps to the first line", () => {
    renderWait(true);
    expect(screen.getByText(zh(FIRST_TOKEN_WAIT_ROTATION_KEYS[0]))).toBeTruthy();

    act(() => {
      vi.advanceTimersByTime(FIRST_TOKEN_WAIT_ROTATE_MS);
    });
    expect(screen.getByText(zh(FIRST_TOKEN_WAIT_ROTATION_KEYS[1]))).toBeTruthy();

    act(() => {
      vi.advanceTimersByTime(FIRST_TOKEN_WAIT_ROTATE_MS);
    });
    expect(screen.getByText(zh(FIRST_TOKEN_WAIT_ROTATION_KEYS[2]))).toBeTruthy();

    // Advance through remaining late lines to wrap.
    act(() => {
      vi.advanceTimersByTime(FIRST_TOKEN_WAIT_ROTATE_MS * 4);
    });
    expect(screen.getByText(zh(FIRST_TOKEN_WAIT_ROTATION_KEYS[0]))).toBeTruthy();
  });

  it("resets to the first line when a new wait starts", () => {
    const { rerender } = render(
      <LocaleProvider>
        <FirstTokenWaitLabel active />
      </LocaleProvider>,
    );
    act(() => {
      vi.advanceTimersByTime(FIRST_TOKEN_WAIT_ROTATE_MS * 2);
    });
    expect(screen.getByText(zh(FIRST_TOKEN_WAIT_ROTATION_KEYS[2]))).toBeTruthy();

    rerender(
      <LocaleProvider>
        <FirstTokenWaitLabel active={false} />
      </LocaleProvider>,
    );
    rerender(
      <LocaleProvider>
        <FirstTokenWaitLabel active />
      </LocaleProvider>,
    );
    expect(screen.getByText(zh(FIRST_TOKEN_WAIT_ROTATION_KEYS[0]))).toBeTruthy();
  });
});
