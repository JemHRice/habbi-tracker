/**
 * The celebration overlay: Habbi, a warm line of copy, and — for a finished
 * day — a scatter of original petals.
 *
 * Every message is encouraging. The "last one left" rung is the only one that
 * mentions anything outstanding, and it does so as an invitation.
 */

import { useEffect } from "react";

import { Habbi, type HabbiPose } from "../Habbi";
import styles from "./Celebration.module.css";
import type { CelebrationTier } from "./useCelebrationLadder";

interface CelebrationProps {
  tier: CelebrationTier | null;
  onDismiss: () => void;
}

const COPY: Record<CelebrationTier, { pose: HabbiPose; title: string; body: string; ms: number }> = {
  halfway: {
    pose: "cheer",
    title: "Yippee — halfway!",
    body: "Lovely going.",
    ms: 2200,
  },
  lastOne: {
    pose: "encourage",
    title: "Just one left",
    body: "Let's keep going.",
    ms: 2600,
  },
  complete: {
    pose: "cheer",
    title: "That's your day!",
    body: "Every single one. Habbi is thrilled.",
    ms: 4200,
  },
};

/** Eight petals, placed around the burst. Original shapes, in palette. */
const PETALS = Array.from({ length: 8 }, (_, index) => index);
const PETAL_COLOURS = ["var(--rose)", "var(--blush)", "var(--gold)", "var(--sky)"];

export function Celebration({ tier, onDismiss }: CelebrationProps) {
  useEffect(() => {
    if (!tier) return;
    const timer = window.setTimeout(onDismiss, COPY[tier].ms);
    return () => window.clearTimeout(timer);
  }, [tier, onDismiss]);

  if (!tier) return null;

  const { pose, title, body } = COPY[tier];
  const isBig = tier === "complete";

  return (
    <div
      className={`${styles.overlay} ${isBig ? styles.big : ""}`}
      role="status"
      aria-live="polite"
      onClick={onDismiss}
    >
      <div className={styles.card}>
        {isBig ? (
          <div className={styles.petals} aria-hidden="true">
            {PETALS.map((index) => (
              <svg
                key={index}
                viewBox="0 0 20 20"
                className={styles.petal}
                style={
                  {
                    "--angle": `${index * 45}deg`,
                    "--delay": `${index * 60}ms`,
                    color: PETAL_COLOURS[index % PETAL_COLOURS.length],
                  } as React.CSSProperties
                }
              >
                <path
                  d="M10 1 C14 5, 14 11, 10 19 C6 11, 6 5, 10 1 Z"
                  fill="currentColor"
                />
              </svg>
            ))}
          </div>
        ) : null}

        <Habbi pose={pose} size={isBig ? 168 : 116} />
        <p className={styles.title}>{title}</p>
        <p className={styles.body}>{body}</p>
      </div>
    </div>
  );
}
