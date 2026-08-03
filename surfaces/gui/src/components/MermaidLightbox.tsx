import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { createPortal } from "react-dom";
import { useI18n } from "../i18n";

const MIN_SCALE = 0.4;
const MAX_SCALE = 4;

type MermaidLightboxProps = {
  svg: string;
  onClose: () => void;
  onExportSvg?: () => void;
  onExportPng?: () => void;
};

export function MermaidLightbox({
  svg,
  onClose,
  onExportSvg,
  onExportPng,
}: MermaidLightboxProps): JSX.Element {
  const { t } = useI18n();
  const [scale, setScale] = useState(1);
  const [tx, setTx] = useState(0);
  const [ty, setTy] = useState(0);
  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    originTx: number;
    originTy: number;
  } | null>(null);
  const viewportRef = useRef<HTMLDivElement | null>(null);

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

  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    function onWheel(event: WheelEvent) {
      event.preventDefault();
      const delta = event.deltaY > 0 ? -0.1 : 0.1;
      setScale((prev) => Math.min(MAX_SCALE, Math.max(MIN_SCALE, prev + delta)));
    }
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  function onPointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return;
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originTx: tx,
      originTy: ty,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function onPointerMove(event: ReactPointerEvent<HTMLDivElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    setTx(drag.originTx + (event.clientX - drag.startX));
    setTy(drag.originTy + (event.clientY - drag.startY));
  }

  function onPointerUp(event: ReactPointerEvent<HTMLDivElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    dragRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  return createPortal(
    <div
      className="mermaid-lightbox"
      data-testid="mermaid-lightbox"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div className="mermaid-lightbox-toolbar" onClick={(e) => e.stopPropagation()}>
        {onExportSvg && (
          <button type="button" onClick={() => onExportSvg()}>
            {t("mermaid.exportSvg")}
          </button>
        )}
        {onExportPng && (
          <button type="button" onClick={() => onExportPng()}>
            {t("mermaid.exportPng")}
          </button>
        )}
        <button type="button" className="mermaid-lightbox-close" onClick={onClose} aria-label="Close">
          ×
        </button>
      </div>
      <div
        ref={viewportRef}
        className="mermaid-lightbox-viewport"
        onClick={(e) => e.stopPropagation()}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <div
          className="mermaid-lightbox-stage"
          style={{ transform: `translate(${tx}px, ${ty}px) scale(${scale})` }}
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      </div>
    </div>,
    document.body,
  );
}
