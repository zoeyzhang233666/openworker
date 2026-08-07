import { useEffect, useState } from "react";
import { useI18n, type MessageKey } from "./i18n";
import {
  FIRST_TOKEN_WAIT_ROTATE_MS,
  advanceFirstTokenWaitIndex,
  waitRotationKeys,
  type WaitCopyPool,
} from "./firstTokenWaitCopy";

/** Lobster rotating wait label for empty windows (D-076 / D-079). */
export function FirstTokenWaitLabel({
  active,
  pool = "first",
}: {
  active: boolean;
  pool?: WaitCopyPool;
}) {
  const { t } = useI18n();
  const [index, setIndex] = useState(0);
  const [show, setShow] = useState(false);
  const keys = waitRotationKeys(pool);

  useEffect(() => {
    if (!active) {
      setShow(false);
      setIndex(0);
      return;
    }
    setIndex(0);
    setShow(true);
    const timer = window.setInterval(() => {
      setIndex((i) => advanceFirstTokenWaitIndex(i, keys.length));
    }, FIRST_TOKEN_WAIT_ROTATE_MS);
    return () => window.clearInterval(timer);
  }, [active, pool, keys.length]);

  if (!active || !show) return null;

  const len = keys.length;
  const safe = len <= 0 ? 0 : ((index % len) + len) % len;
  const labelKey = keys[safe] || keys[0];

  return (
    <div className="waiting-transcript" data-testid="first-token-wait" data-pool={pool}>
      <div className="waiting-row" aria-live="polite">
        <span className="waiting-spinner" />
        <span>{t(labelKey as MessageKey)}</span>
      </div>
    </div>
  );
}
