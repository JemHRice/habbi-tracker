/**
 * A single day, opened from the calendar.
 *
 * Today and yesterday stay editable; anything older is read-only. The UI
 * disables the controls rather than letting a tap turn into a 403 — the API
 * would refuse it anyway, and being told "no" is a worse experience than never
 * being offered.
 */

import { useNavigate, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { useComplete, useDay, useUncomplete } from "../api/queries";
import type { HabitRef } from "../api/types";
import { Habbi } from "../components/Habbi";
import { HabitRow } from "../components/HabitRow";
import { Notice } from "../components/Notice";
import styles from "./DayDetail.module.css";
import { useState } from "react";

export function DayDetail() {
  const { date = "" } = useParams();
  const navigate = useNavigate();
  const { data, isPending, isError } = useDay(date);
  const complete = useComplete();
  const uncomplete = useUncomplete();
  const [notice, setNotice] = useState<string | null>(null);

  const explain = (error: unknown) =>
    setNotice(
      error instanceof ApiError && error.isOffline
        ? "We'll need signal for that."
        : "That didn't go through.",
    );

  const heading = new Date(`${date}T00:00:00`).toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <div>
      <button type="button" className={styles.back} onClick={() => navigate(-1)}>
        ‹ Back
      </button>

      <h1 className={styles.heading}>{heading}</h1>

      {isPending ? <p className={styles.quiet}>Loading…</p> : null}
      {isError ? <p className={styles.quiet}>We couldn't load that day.</p> : null}

      {data ? (
        data.no_data ? (
          <div className={styles.noData}>
            <Habbi pose="oops" size={140} label="Habbi with her paws over her mouth" />
            <p className={styles.noDataText}>No data here</p>
            <p className={styles.quiet}>Nothing was recorded on this day.</p>
          </div>
        ) : (
          <>
            <p className={styles.finalPct}>
              {data.final_pct === null
                ? "A rest day — nothing was scheduled."
                : `${Math.round(data.final_pct * 100)}% of what was scheduled`}
            </p>

            {!data.editable ? (
              <p className={styles.lockedNote}>
                This day is complete and can no longer be changed.
              </p>
            ) : null}

            {data.completed.length > 0 ? (
              <section aria-label="Done">
                <h2 className={styles.sectionHeading}>Done</h2>
                <ul className={styles.list}>
                  {data.completed.map((entry) => (
                    <HabitRow
                      key={`${entry.habit.id}-${entry.completed_at}`}
                      habit={entry.habit}
                      completed
                      isBonus={entry.is_bonus}
                      disabled={!data.editable}
                      onToggle={
                        data.editable
                          ? (habit: HabitRef) =>
                              uncomplete.mutate(
                                { habit_id: habit.id, date },
                                { onError: explain },
                              )
                          : undefined
                      }
                    />
                  ))}
                </ul>
              </section>
            ) : null}

            {data.not_completed.length > 0 ? (
              <section aria-label="Not done">
                <h2 className={styles.sectionHeading}>Not done</h2>
                <ul className={styles.list}>
                  {data.not_completed.map((habit) => (
                    <HabitRow
                      key={habit.id}
                      habit={habit}
                      disabled={!data.editable}
                      onToggle={
                        data.editable
                          ? () =>
                              complete.mutate(
                                { habit_id: habit.id, date },
                                { onError: explain },
                              )
                          : undefined
                      }
                    />
                  ))}
                </ul>
              </section>
            ) : null}
          </>
        )
      ) : null}

      <Notice message={notice} onDismiss={() => setNotice(null)} />
    </div>
  );
}
