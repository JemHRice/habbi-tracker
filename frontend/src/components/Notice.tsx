/**
 * A gentle, transient message.
 *
 * Used for the things that can go wrong — losing signal, mostly. The tone is
 * deliberately soft and the styling deliberately warm: even a failure in this
 * app should not feel like a telling-off.
 */

import { useEffect } from "react";

import styles from "./Notice.module.css";

interface NoticeProps {
  message: string | null;
  onDismiss: () => void;
  /** How long before it fades by itself. */
  ms?: number;
}

export function Notice({ message, onDismiss, ms = 3200 }: NoticeProps) {
  useEffect(() => {
    if (!message) return;
    const timer = window.setTimeout(onDismiss, ms);
    return () => window.clearTimeout(timer);
  }, [message, ms, onDismiss]);

  if (!message) return null;

  return (
    <div className={styles.notice} role="status" aria-live="polite">
      {message}
    </div>
  );
}
