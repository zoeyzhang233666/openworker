import { QRCodeCanvas } from "qrcode.react";

/**
 * iLink returns ``qrcode_img_content`` as a WeChat scan URL (e.g.
 * ``https://weixin.qq.com/x/...``), not a raster image. Render it as a QR code.
 * Legacy payloads may still be data-URLs or direct image links.
 */
export function WeixinQrImage({
  payload,
  alt,
  className,
  testId,
  size = 224,
}: {
  payload: string;
  alt: string;
  className?: string;
  testId?: string;
  size?: number;
}) {
  const value = (payload || "").trim();
  if (!value) return null;

  if (isDirectImageSrc(value)) {
    const src =
      value.startsWith("data:") || /^https?:\/\//i.test(value)
        ? value
        : `data:image/png;base64,${value.replace(/\s+/g, "")}`;
    return (
      <img
        src={src}
        alt={alt}
        className={className}
        data-testid={testId}
      />
    );
  }

  return (
    <QRCodeCanvas
      value={value}
      size={size}
      level="M"
      includeMargin
      className={className}
      data-testid={testId}
      role="img"
      aria-label={alt}
    />
  );
}

function isDirectImageSrc(value: string): boolean {
  if (value.startsWith("data:image/")) return true;
  if (/^https?:\/\//i.test(value) && /\.(png|jpe?g|gif|webp|svg)(\?|#|$)/i.test(value)) {
    return true;
  }
  // Some iLink builds return raw base64 PNG without a data-URL prefix.
  if (/^[A-Za-z0-9+/=\s]+$/.test(value) && value.length > 256) {
    return true;
  }
  return false;
}

export function resolveWeixinQrSrc(value: string): string {
  const trimmed = (value || "").trim();
  if (!trimmed) return trimmed;
  if (trimmed.startsWith("data:") || trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return trimmed;
  }
  if (/^[A-Za-z0-9+/=\s]+$/.test(trimmed) && trimmed.length > 256) {
    return `data:image/png;base64,${trimmed.replace(/\s+/g, "")}`;
  }
  return trimmed;
}
