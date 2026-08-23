/**
 * "Add something extra" — the picker for logging a bonus.
 *
 * A bonus is a habit done on a day it wasn't asked for. It joins the completed
 * pile but never touches the percentage, so the copy here is framed as a
 * flourish rather than as progress toward anything.
 */

import { useEffect, useRef } from "react";

import type { HabitRef } from "../api/types";
import styles from "./ExtrasPicker.module.css";

interface ExtrasPickerProps {
  open: boolean;
  extras: HabitRef[];
  onPick: (habit: HabitRef) => void;
  onClose: () => void;
}

export function ExtrasPicker({ open, extras, onPick, onClose }: ExtrasPickerProps) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className={styles.scrim} onClick={onClose}>
      <div
        className={styles.sheet}
        role="dialog"
        aria-modal="true"
        aria-label="Add something extra"
        onClick={(event) => event.stopPropagation()}
      >
        <div className={styles.header}>
          <div>
            <h2 className={styles.title}>Something extra</h2>
            <p className={styles.subtitle}>A bonus — it won't change your percentage.</p>
          </div>
          <button
            ref={closeRef}
            type="button"
            className={styles.close}
            onClick={onClose}
            aria-label="Close"
          >
            <svg viewBox="0 0 24 24" width={20} height={20} aria-hidden="true">
              <path
                d="M6 6l12 12M18 6L6 18"
                fill="none"
                stroke="currentColor"
                strokeWidth={2.4}
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>

        {extras.length === 0 ? (
          <p className={styles.empty}>
            Everything on your list is already scheduled today.
          </p>
        ) : (
          <ul className={styles.list}>
            {extras.map((habit) => (
              <li key={habit.id}>
                <button
                  type="button"
                  className={styles.option}
                  style={{ borderLeftColor: habit.bucket_color_hex }}
                  onClick={() => onPick(habit)}
                >
                  <span className={styles.optionName}>{habit.name}</span>
                  <span className={styles.optionMeta}>{habit.bucket_name}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
