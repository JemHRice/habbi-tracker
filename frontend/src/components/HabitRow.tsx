/**
 * A single habit on the Today list, in either state.
 *
 * Active items are large tap targets with an empty circle; completed ones strike
 * through and sit quietly in the pile. Tapping either one toggles it, so
 * un-ticking is exactly as easy as ticking.
 */

import type { HabitRef } from "../api/types";
import styles from "./HabitRow.module.css";

interface HabitRowProps {
  habit: HabitRef;
  completed?: boolean;
  isBonus?: boolean;
  disabled?: boolean;
  onToggle?: (habit: HabitRef) => void;
}

export function HabitRow({
  habit,
  completed = false,
  isBonus = false,
  disabled = false,
  onToggle,
}: HabitRowProps) {
  const interactive = Boolean(onToggle) && !disabled;

  const content = (
    <>
      <span
        className={styles.marker}
        style={{ borderColor: habit.bucket_color_hex }}
        aria-hidden="true"
      >
        {completed ? (
          <svg viewBox="0 0 24 24" className={styles.tick}>
            <path
              d="M5 13l4.5 4.5L19 7"
              fill="none"
              stroke="currentColor"
              strokeWidth={3}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        ) : null}
      </span>

      <span className={styles.text}>
        <span className={styles.name}>{habit.name}</span>
        <span className={styles.meta}>
          {habit.bucket_name}
          {habit.time_cap_minutes ? ` · ${habit.time_cap_minutes} min` : ""}
          {isBonus ? " · bonus" : ""}
        </span>
      </span>
    </>
  );

  const className = [
    styles.row,
    completed ? styles.done : styles.active,
    isBonus ? styles.bonus : "",
    disabled ? styles.locked : "",
  ]
    .filter(Boolean)
    .join(" ");

  if (!interactive) {
    return (
      <li className={className} style={{ "--bucket": habit.bucket_color_hex } as React.CSSProperties}>
        <div className={styles.inner}>{content}</div>
      </li>
    );
  }

  return (
    <li className={className} style={{ "--bucket": habit.bucket_color_hex } as React.CSSProperties}>
      <button
        type="button"
        className={styles.inner}
        onClick={() => onToggle?.(habit)}
        aria-pressed={completed}
      >
        {content}
      </button>
    </li>
  );
}
