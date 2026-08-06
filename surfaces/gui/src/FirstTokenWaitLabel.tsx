import { useEffect, useState } from "react";
import { useI18n, type MessageKey } from "./i18n";
import {
  FIRST_TOKEN_WAIT_ROTATE_MS,
  FIRST_TOKEN_WAIT_ROTATION_KEYS,
  advanceFirstTokenWaitIndex,
  type FirstTokenWaitKey,
} from "./firstTokenWaitCopy";

/** Lobster rotating wait label for the first-token empty window (D-076). */
export function FirstTokenWaitLabel({ active }: { active: boolean }) {
  const { t } = useI18n();
  const [index, setIndex] = useState(0);
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (!active) {
      setShow(false);
      setIndex(0);
      return;
    }
    setIndex(0);
    setShow(true);
    const timer = window.setInterval(() => {
      setIndex((i) => advanceFirstTokenWaitIndex(i));
    }, FIRST_TOKEN_WAIT_ROTATE_MS);
    return () => window.clearInterval(timer);
  }, [active]);

  if (!active || !show) return null;

  const labelKey = FIRST_TOKEN_WAIT_ROTATION_KEYS[
    nextSafeIndex(index)
  ] as FirstTokenWaitKey;

  return (
    <div className="waiting-transcript" data-testid="first-token-wait">
      <div className="waiting-row" aria-live="polite">
        <span className="waiting-spinner" />
        <span>{t(labelKey as MessageKey)}</span>
      </div>
    </div>
  );
}

function nextSafeIndex(index: number): number {
  const len = FIRST_TOKEN_WAIT_ROTATION_KEYS.length;
  if (len <= 0) return 0;
  return ((index % len) + len) % len;
}
