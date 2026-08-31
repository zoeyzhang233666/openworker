import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { WeixinQrImage } from "./WeixinQrImage";

afterEach(cleanup);

describe("WeixinQrImage", () => {
  it("renders a QR canvas for iLink scan URLs", () => {
    render(
      <WeixinQrImage
        payload="https://weixin.qq.com/x/cAbCdEfGhIj"
        alt="微信登录二维码"
        testId="weixin-qr-image"
      />,
    );
    const node = screen.getByTestId("weixin-qr-image");
    expect(node.tagName).toBe("CANVAS");
  });

  it("renders an img for direct image URLs", () => {
    render(
      <WeixinQrImage
        payload="https://example.test/weixin-qr.png"
        alt="微信登录二维码"
        testId="weixin-qr-image"
      />,
    );
    const node = screen.getByTestId("weixin-qr-image") as HTMLImageElement;
    expect(node.tagName).toBe("IMG");
    expect(node.src).toContain("weixin-qr.png");
  });
});
