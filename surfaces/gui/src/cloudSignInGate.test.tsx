import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { CloudSignInInline } from "./components/connectors/CloudSignIn";
import { CLOUD_SIGNIN_ENABLED } from "./product";

afterEach(() => cleanup());

describe("CLOUD_SIGNIN_ENABLED trial gate", () => {
  it("keeps the product flag off for ChemClaw trial builds", () => {
    expect(CLOUD_SIGNIN_ENABLED).toBe(false);
  });

  it("renders coming-soon copy instead of a sign-in button", () => {
    render(<CloudSignInInline />);
    expect(screen.getByTestId("cloud-signin-disabled")).toBeTruthy();
    expect(screen.queryByTestId("inline-cloud-sign-in")).toBeNull();
    expect(screen.getByText(/云连接即将上线|cloud connection is coming soon/i)).toBeTruthy();
  });
});
