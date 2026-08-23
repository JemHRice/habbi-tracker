/**
 * Today — the home screen.
 *
 * Renders exactly what the API returns, in the order it returns it. The active
 * list is already sorted by the backend (`anytime` last, then `sort_order`), so
 * it is never re-sorted here; the completed pile arrives in tick order.
 *
 * Ticking is optimistic: the item moves instantly and the server's response
 * replaces the prediction. If the request fails, the move is rolled back and a
 * soft notice explains why.
 */

import { useState } from "react";

import { ApiError } from "../api/client";
import { useAddBonus, useComplete, useToday, useUncomplete } from "../api/queries";
import type { HabitRef } from "../api/types";
import { Celebration } from "../components/celebration/Celebration";
import { useCelebrationLadder } from "../components/celebration/useCelebrationLadder";
import { DailyProgress } from "../components/DailyProgress";
import { ExtrasPicker } from "../components/ExtrasPicker";
import { Habbi } from "../components/Habbi";
import { HabitRow } from "../components/HabitRow";
import { Notice } from "../components/Notice";
import styles from "./Today.module.css";

function friendlyDate(iso: string): string {
  const date = new Date(`${iso}T00:00:00`);
  return date.toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

export function Today() {
  const { data, isPending, isError, refetch } = useToday();
  const complete = useComplete();
  const uncomplete = useUncomplete();
  const addBonus = useAddBonus();

  const [pickerOpen, setPickerOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const { tier, dismiss } = useCelebrationLadder(data);

  const explain = (error: unknown) => {
    if (error instanceof ApiError) {
      setNotice(error.isOffline ? "We'll need signal for that." : error.message);
    } else {
      setNotice("That didn't go through. Try again in a moment.");
    }
  };

  if (isPending) {
    return <p className={styles.quiet}>Getting your day…</p>;
  }

  if (isError || !data) {
    return (
      <div className={styles.problem}>
        <Habbi pose="oops" size={120} />
        <p className={styles.quiet}>We couldn't reach your board just now.</p>
        <button type="button" className={styles.retry} onClick={() => void refetch()}>
          Try again
        </button>
      </div>
    );
  }

  const onToggleActive = (habit: HabitRef) =>
    complete.mutate({ habit_id: habit.id, date: data.date }, { onError: explain });

  const onToggleCompleted = (habit: HabitRef) =>
    uncomplete.mutate({ habit_id: habit.id, date: data.date }, { onError: explain });

  const onPickExtra = (habit: HabitRef) => {
    setPickerOpen(false);
    addBonus.mutate({ habit_id: habit.id, date: data.date, habit }, { onError: explain });
  };

  return (
    <div className={styles.wrap}>
      <header className={styles.header}>
        <h1 className={styles.heading}>Today</h1>
        <p className={styles.date}>{friendlyDate(data.date)}</p>
      </header>

      <DailyProgress
        pct={data.daily_pct}
        doneCount={data.done_count}
        remainingCount={data.remaining_count}
      />

      {data.active.length > 0 ? (
        <ul className={styles.list}>
          {data.active.map((habit) => (
            <HabitRow key={habit.id} habit={habit} onToggle={onToggleActive} />
          ))}
        </ul>
      ) : data.daily_pct === null ? (
        <div className={styles.restday}>
          <Habbi pose="encourage" size={128} />
          <p className={styles.quiet}>Nothing scheduled today.</p>
        </div>
      ) : (
        <div className={styles.allDone}>
          <p className={styles.allDoneText}>Everything's done. 🌿</p>
        </div>
      )}

      <button
        type="button"
        className={styles.extrasButton}
        onClick={() => setPickerOpen(true)}
      >
        <span aria-hidden="true">+</span> Add something extra
      </button>

      {data.completed.length > 0 ? (
        <section className={styles.pile} aria-label="Completed">
          <h2 className={styles.pileHeading}>Done</h2>
          <ul className={styles.list}>
            {data.completed.map((entry) => (
              <HabitRow
                key={`${entry.habit.id}-${entry.completed_at}`}
                habit={entry.habit}
                completed
                isBonus={entry.is_bonus}
                onToggle={onToggleCompleted}
              />
            ))}
          </ul>
        </section>
      ) : null}

      <ExtrasPicker
        open={pickerOpen}
        extras={data.available_extras}
        onPick={onPickExtra}
        onClose={() => setPickerOpen(false)}
      />

      <Celebration tier={tier} onDismiss={dismiss} />
      <Notice message={notice} onDismiss={() => setNotice(null)} />
    </div>
  );
}
