import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import type { Connector } from "../../api";
import { AvailableDetail } from "./AvailableDetail";
import { ConnectorsList } from "./ConnectorsList";

afterEach(cleanup);

function connector(overrides: Partial<Connector> = {}): Connector {
  return {
    name: "weixin",
    title: "个人微信",
    icon: "",
    blurb: "官方 iLink 私聊",
    auth: "qr",
    two_way: true,
    channels: false,
    available: true,
    fields: [],
    instructions: [],
    connected: false,
    account: null,
    enabled: true,
    brand_color: "#07c160",
    logo: "weixin",
    allowed_users: [],
    tools: [],
    managed: false,
    managed_profile: false,
    ...overrides,
  };
}

describe("Channel connector capability and status UI", () => {
  it("shows only truthful Weixin capabilities", () => {
    render(
      <AvailableDetail
        c={connector({
          capabilities: {
            direct_messages: true,
            group_chat: false,
            group_mentions: false,
            receive_files: true,
            send_files: true,
            receive_images: true,
            send_images: true,
          },
        })}
        cloud={null}
        onChanged={() => {}}
      />,
    );
    const chips = screen.getByTestId("channel-capabilities");
    expect(chips.textContent).toContain("私聊");
    expect(chips.textContent).toContain("文件双向传输");
    expect(chips.textContent).not.toContain("群聊");
  });

  it("surfaces QR authentication state in the connected list", () => {
    render(
      <ConnectorsList
        connectors={[
          connector({
            connected: true,
            channel_status: {
              state: "auth_required",
              authenticated: false,
              queue_length: 0,
              reconnect_count: 0,
              details: { qr_url: "https://example.test/qr" },
            },
          }),
        ]}
        cloud={null}
        slack={null}
        onOpen={() => {}}
        onChanged={() => {}}
      />,
    );
    const row = screen.getByTestId("connector-weixin");
    expect(row.textContent).toContain("扫描二维码以完成连接");
    expect(row.textContent).toContain("需要扫码");
  });

  it("shows Weixin QR on AccountsDetail for single-account auth_required", async () => {
    const { AccountsDetail } = await import("./AccountsDetail");
    render(
      <AccountsDetail
        c={connector({
          connected: true,
          accounts: [
            {
              account_id: "default",
              name: "个人微信 iLink",
              default: true,
              managed: false,
            },
          ],
          channel_status: {
            state: "auth_required",
            authenticated: false,
            queue_length: 0,
            reconnect_count: 0,
            details: {
              qr_url: "https://example.test/weixin-qr.png",
              accounts: [
                {
                  account_id: "default",
                  state: "auth_required",
                  details: { qr_url: "https://example.test/weixin-qr.png" },
                },
              ],
            },
          },
        })}
        cloud={null}
        slack={null}
        onChanged={() => {}}
      />,
    );
    const img = screen.getByTestId("accounts-weixin-qr-image") as HTMLImageElement;
    expect(img.tagName).toBe("IMG");
    expect(img.src).toContain("weixin-qr.png");
    expect(screen.getByTestId("channel-account-status").textContent).toContain(
      "需要扫码",
    );
  });

  it("renders CowAgent-style WeixinDetail with a large QR code", async () => {
    const { WeixinDetail } = await import("./WeixinDetail");
    render(
      <WeixinDetail
        c={connector({
          connected: true,
          accounts: [
            {
              account_id: "default",
              name: "个人微信 iLink / 等待扫码",
              default: true,
              managed: false,
            },
          ],
          channel_status: {
            state: "auth_required",
            authenticated: false,
            queue_length: 0,
            reconnect_count: 0,
            details: {
              qr_url: "https://weixin.qq.com/x/cAbCdEfGhIj",
              accounts: [
                {
                  account_id: "default",
                  state: "auth_required",
                  details: { qr_url: "https://weixin.qq.com/x/cAbCdEfGhIj" },
                },
              ],
            },
          },
        })}
        cloud={null}
        slack={null}
        onChanged={() => {}}
      />,
    );
    expect(screen.getByTestId("weixin-detail")).toBeTruthy();
    expect(screen.getByTestId("weixin-qr-image").tagName).toBe("CANVAS");
    expect(screen.getByTestId("weixin-status-label").textContent).toContain(
      "请用手机微信扫描下方二维码",
    );
  });

  it("falls back to top-level qr_url when accounts array is missing", async () => {
    const { AccountsDetail } = await import("./AccountsDetail");
    render(
      <AccountsDetail
        c={connector({
          connected: true,
          accounts: [{ account_id: "default", name: "微信", default: true, managed: false }],
          channel_status: {
            state: "auth_required",
            authenticated: false,
            details: { qr_url: "data:image/png;base64,abc" },
          },
        })}
        cloud={null}
        slack={null}
        onChanged={() => {}}
      />,
    );
    expect(
      (screen.getByTestId("accounts-weixin-qr-image") as HTMLImageElement).src,
    ).toContain("data:image/png");
  });
});
