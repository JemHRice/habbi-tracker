/**
 * The day's progress, numerically and visually.
 *
 * The ring can only fill — it has no "over" state and no colour that reads as
 * bad, because the percentage it draws cannot exceed 100% and an unfinished day
 * is not a failure. A day with nothing scheduled is a rest day, shown as such
 * rather than as 0%.
 */

import styles from "./DailyProgress.module.css";

interface DailyProgressProps {
  /** Fraction from 0 to 1, or null for a rest day. */
  pct: number | null;
  doneCount: number;
  remainingCount: number;
}

const RADIUS = 52;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function DailyProgress({ pct, doneCount, remainingCount }: DailyProgressProps) {
  if (pct === null) {
    return (
      <section className={styles.wrap} aria-label="Today's progress">
        <p className={styles.restTitle}>A rest day</p>
        <p className={styles.restBody}>Nothing scheduled. Enjoy it.</p>
      </section>
    );
  }

  const percent = Math.round(pct * 100);
  const filled = CIRCUMFERENCE * pct;

  return (
    <section className={styles.wrap} aria-label="Today's progress">
      <div className={styles.ringWrap}>
        <svg viewBox="0 0 120 120" className={styles.ring} aria-hidden="true">
          <circle
            cx={60}
            cy={60}
            r={RADIUS}
            fill="none"
            stroke="var(--rose-soft)"
            strokeWidth={11}
          />
          <circle
            cx={60}
            cy={60}
            r={RADIUS}
            fill="none"
            stroke="var(--rose)"
            strokeWidth={11}
            strokeLinecap="round"
            strokeDasharray={`${filled} ${CIRCUMFERENCE}`}
            transform="rotate(-90 60 60)"
            className={styles.fill}
          />
        </svg>
        <div className={styles.readout}>
          <span className={styles.percent}>{percent}%</span>
        </div>
      </div>

      <p className={styles.caption}>
        {remainingCount === 0
          ? `All ${doneCount} done`
          : `${doneCount} done · ${remainingCount} to go`}
      </p>
    </section>
  );
}
