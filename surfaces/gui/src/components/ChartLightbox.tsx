import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useI18n } from "../i18n";

type ChartLightboxProps = {
  onClose: () => void;
  children: ReactNode;
};

/** Fullscreen portal shell for charts (Esc / close button). */
export function ChartLightbox({ onClose, children }: ChartLightboxProps): JSX.Element {
  const { t } = useI18n();

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return createPortal(
    <div
      className="chart-lightbox"
      data-testid="chart-lightbox"
      role="dialog"
      aria-modal="true"
      aria-label={t("chart.fullscreen")}
    >
      <div className="chart-lightbox-toolbar">
        <button
          type="button"
          className="chart-lightbox-close"
          onClick={onClose}
          aria-label="Close"
        >
          ×
        </button>
      </div>
      <div className="chart-lightbox-body">{children}</div>
    </div>,
    document.body,
  );
}
