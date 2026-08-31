import { useEffect, useState } from "react";
import {
  connectConnector,
  disconnectAccount,
  disconnectConnector,
  submitWeixinVerifyCode,
  type AccountRow,
  type Connector,
} from "../../api";
import { ConnectorBadge } from "../../connectors/ConnectorIcon";
import { ConnectSetup } from "../ManageTabs";
import type { DetailProps } from "./ConnectorsSection";
import { ToolsDisclosure } from "./ToolsDisclosure";
import { WeixinQrImage } from "./WeixinQrImage";
import { FOOT, GRP, GRP_H, PILL_ACCENT, ROW, TAG_QUIET, XBTN } from "./ui";
import { useI18n } from "../../i18n";

/**
 * CowAgent-style Weixin connect: primary surface is a big QR code.
 * Advanced token/API fields stay collapsed — most users never need them.
 */
export function WeixinDetail({ c, cloud, onChanged }: DetailProps) {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [verifyCode, setVerifyCode] = useState("");

  const status = c.channel_status;
  const nested = status?.details?.accounts ?? [];
  const accounts = (c.accounts ?? []).filter(
    (account): account is AccountRow => "account_id" in account,
  );
  const defaultAccountId = accounts.find((account) => account.default)?.account_id;
  const primary =
    nested.find((row) => row.state === "auth_required") ||
    nested.find((row) => row.account_id === defaultAccountId) ||
    nested[0];
  const qrUrl =
    primary?.details?.qr_url ||
    status?.details?.qr_url ||
    "";
  const state = primary?.state || status?.state || "";
  const accountId = primary?.account_id || defaultAccountId || "default";
  const needsVerifyCode = Boolean(primary?.details?.needs_verify_code);
  const lastError = primary?.last_error || status?.last_error || "";
  const needsScan =
    state === "auth_required" || Boolean(qrUrl) || /等待扫码/.test(String(c.account || ""));
  const authenticated = state === "connected" && !needsScan && Boolean(status?.authenticated);

  const startQrLogin = async () => {
    setBusy(true);
    setError(null);
    try {
      // Re-connect refreshes the gateway adapter and fetches a fresh QR code.
      // Do not disconnect first — that wipes the stored account profile.
      const result = await connectConnector(c.name, {});
      if (!result.ok) {
        setError(result.error || t("无法开始微信扫码"));
      }
      onChanged();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : t("无法开始微信扫码"));
    } finally {
      setBusy(false);
    }
  };

  // Landed on a half-connected profile without a QR → kick gateway once.
  useEffect(() => {
    if (!c.connected || qrUrl || authenticated || busy) return;
    void startQrLogin();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [c.connected, qrUrl, authenticated]);

  return (
    <div data-testid="weixin-detail">
      <div className="flex items-center gap-3.5 mb-5">
        <ConnectorBadge connector={c} size={44} title={c.title} />
        <div className="min-w-0 flex-1">
          <h2 className="text-[20px] font-semibold tracking-tight leading-tight">
            {c.title}
          </h2>
          <div className="text-[12.5px] text-muted flex items-center gap-1.5">
            <span
              className={`w-2 h-2 rounded-full ${
                authenticated ? "bg-ok" : needsScan ? "bg-warnInk" : "bg-muted"
              }`}
            />
            <span data-testid="weixin-status-label">
              {authenticated
                ? t("已连接 · 仅支持私聊")
                : needsScan
                  ? t("请用手机微信扫描下方二维码")
                  : t("Not connected")}
            </span>
          </div>
        </div>
        {c.connected && (
          <button
            className="text-[12.5px] text-danger/80 hover:text-danger shrink-0"
            onClick={async () => {
              await disconnectConnector(c.name);
              onChanged();
            }}
          >
            {t("Disconnect")}
          </button>
        )}
      </div>

      <div className={GRP_H + " !mt-0"}>{t("扫码登录")}</div>
      <div className={GRP} data-testid="weixin-qr-panel">
        <div className={ROW + " flex-col items-center gap-3 !py-5"}>
          {qrUrl ? (
            <>
              <WeixinQrImage
                payload={qrUrl}
                alt={t("WeChat sign-in QR code")}
                className="w-56 h-56 bg-white rounded-xl p-3 border border-line"
                testId="weixin-qr-image"
                size={224}
              />
              <div className="text-[13px] text-ink text-center">
                {t("打开手机微信 → 扫一扫 → 确认登录")}
              </div>
              <div className="text-[12px] text-muted text-center">
                {t("官方 iLink 仅支持私聊，不支持群聊。")}
              </div>
            </>
          ) : authenticated ? (
            <div className="text-[13px] text-ink py-6">{t("扫码已完成，私聊通道可用。")}</div>
          ) : (
            <div className="text-[13px] text-muted py-6">
              {busy ? t("正在获取二维码…") : t("还没有二维码")}
            </div>
          )}
          <button
            type="button"
            className={PILL_ACCENT}
            data-testid="weixin-refresh-qr"
            disabled={busy}
            onClick={() => void startQrLogin()}
          >
            {t(busy ? "请稍候…" : qrUrl ? "刷新二维码" : "获取二维码")}
          </button>
          {needsVerifyCode && (
            <div className="w-full max-w-56 flex flex-col gap-2" data-testid="weixin-verify-panel">
              <input
                className="px-2 py-1.5 rounded-lg border border-line bg-paper text-[13px] text-ink outline-none focus:border-accent text-center"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={verifyCode}
                data-testid="weixin-verify-code"
                placeholder={t("Enter the code shown in WeChat")}
                onChange={(event) =>
                  setVerifyCode(event.target.value.replace(/\D/g, "").slice(0, 8))
                }
              />
              <button
                type="button"
                className={PILL_ACCENT}
                data-testid="weixin-submit-verify-code"
                disabled={busy || verifyCode.length < 4}
                onClick={async () => {
                  setBusy(true);
                  setError(null);
                  const result = await submitWeixinVerifyCode(accountId, verifyCode);
                  if (!result.ok) setError(result.error || t("Could not submit the code"));
                  else setVerifyCode("");
                  setBusy(false);
                  onChanged();
                }}
              >
                {t("Submit code")}
              </button>
            </div>
          )}
          {(error || lastError) && (
            <div className="text-[12px] text-danger text-center" data-testid="weixin-qr-error">
              {error || lastError}
            </div>
          )}
        </div>
      </div>

      <button
        type="button"
        className="mt-4 text-[12.5px] text-accent"
        data-testid="weixin-advanced-toggle"
        onClick={() => setShowAdvanced((v) => !v)}
      >
        {t(showAdvanced ? "收起高级选项" : "高级选项（一般无需填写）")}
      </button>

      {showAdvanced && (
        <div className="mt-2" data-testid="weixin-advanced">
          <div className={GRP_H}>{t("Add an account")}</div>
          <div className={GRP}>
            <div className="px-1.5 py-1">
              <ConnectSetup
                c={c}
                cloud={cloud}
                onConnected={() => {
                  setShowAdvanced(false);
                  onChanged();
                }}
              />
            </div>
          </div>
          {accounts.length > 0 && (
            <>
              <div className={GRP_H}>{t("Accounts")}</div>
              <div className={GRP}>
                {accounts.map((a) => (
                  <div key={a.account_id} className={ROW + " text-[13px]"}>
                    <span className="flex-1 min-w-0 truncate">
                      {a.name || a.account_id}
                    </span>
                    <span className={TAG_QUIET}>{a.default ? t("Default") : a.account_id}</span>
                    <button
                      className={XBTN}
                      title={t("Disconnect")}
                      onClick={async () => {
                        await disconnectAccount(c.name, a.account_id);
                        onChanged();
                      }}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      <ToolsDisclosure c={c} onChanged={onChanged} />
      <div className={FOOT + " mt-2"}>
        {t("凭据只保存在本机。断开连接可随时清除。")}
      </div>
    </div>
  );
}

/** Pre-connect entry: one button that immediately starts QR login. */
export function WeixinAvailable({
  c,
  onChanged,
}: {
  c: Connector;
  onChanged: () => void;
}) {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <div data-testid="weixin-available">
      <div className="flex items-center gap-3.5 mb-5">
        <ConnectorBadge connector={c} size={44} title={c.title} />
        <div className="min-w-0 flex-1">
          <h2 className="text-[20px] font-semibold tracking-tight leading-tight">
            {c.title}
          </h2>
          <div className="text-[12.5px] text-muted">{c.blurb}</div>
        </div>
      </div>
      {c.capabilities && (
        <div className="flex flex-wrap gap-1.5 mb-4" data-testid="channel-capabilities">
          <span className={TAG_QUIET}>{t("私聊")}</span>
          <span className={TAG_QUIET}>{t("文件双向传输")}</span>
        </div>
      )}
      <p className="text-[13px] text-ink/90 leading-relaxed mb-4">
        {t("点击下方按钮后将显示微信登录二维码，用手机微信扫码即可，无需填写 Token。")}
      </p>
      <button
        type="button"
        className={PILL_ACCENT}
        data-testid="weixin-start-qr"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setError(null);
          const result = await connectConnector(c.name, {});
          if (!result.ok) setError(result.error || t("无法开始微信扫码"));
          setBusy(false);
          onChanged();
        }}
      >
        {t(busy ? "正在获取二维码…" : "扫码连接个人微信")}
      </button>
      {error && <div className="mt-2 text-[12px] text-danger">{error}</div>}
    </div>
  );
}
