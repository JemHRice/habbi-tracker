/**
 * Habit and bucket management.
 *
 * This screen carries more weight than its "basic settings area" brief
 * suggests: one board is seeded empty on purpose, so every habit that person
 * ever has gets typed in here. It is built to make entering twenty-odd habits
 * bearable rather than to look impressive.
 *
 * Reordering uses up/down buttons rather than drag. Dragging is nicer on a
 * desktop and worse everywhere else — it fights scrolling on a phone and is
 * hostile to keyboards and screen readers.
 */

import { useState } from "react";
import { Link } from "react-router-dom";

import {
  useArchiveHabit,
  useBuckets,
  useCreateBucket,
  useCreateHabit,
  useHabits,
  useReorderHabits,
  useSetSchedule,
  useUpdateHabit,
} from "../api/queries";
import type { BucketOut, HabitOut } from "../api/types";
import { Notice } from "../components/Notice";
import styles from "./Habits.module.css";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function WeekdayPicker({
  value,
  onChange,
}: {
  value: number[];
  onChange: (weekdays: number[]) => void;
}) {
  const toggle = (day: number) =>
    onChange(
      value.includes(day)
        ? value.filter((candidate) => candidate !== day)
        : [...value, day].sort((a, b) => a - b),
    );

  return (
    <div className={styles.weekdays} role="group" aria-label="Scheduled weekdays">
      {WEEKDAYS.map((label, day) => (
        <button
          key={day}
          type="button"
          className={[styles.weekday, value.includes(day) ? styles.weekdayOn : ""]
            .filter(Boolean)
            .join(" ")}
          aria-pressed={value.includes(day)}
          onClick={() => toggle(day)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function HabitEditor({
  habit,
  buckets,
  onDone,
  onNotice,
}: {
  habit: HabitOut;
  buckets: BucketOut[];
  onDone: () => void;
  onNotice: (message: string) => void;
}) {
  const updateHabit = useUpdateHabit();
  const setSchedule = useSetSchedule();
  const archive = useArchiveHabit();

  const [name, setName] = useState(habit.name);
  const [bucketId, setBucketId] = useState(habit.bucket_id);
  const [weekdays, setWeekdays] = useState(habit.weekdays);
  const [cap, setCap] = useState(habit.time_cap_minutes?.toString() ?? "");
  const [anytime, setAnytime] = useState(habit.anytime);
  const [seasonal, setSeasonal] = useState(habit.season_dependent);

  const save = async () => {
    try {
      await updateHabit.mutateAsync({
        id: habit.id,
        patch: {
          name,
          bucket_id: bucketId,
          anytime,
          season_dependent: seasonal,
          target_per_week: weekdays.length,
          ...(cap.trim() === ""
            ? { clear_time_cap: true }
            : { time_cap_minutes: Number(cap) }),
        },
      });
      await setSchedule.mutateAsync({ id: habit.id, weekdays });
      onDone();
    } catch {
      onNotice("Couldn't save that just now.");
    }
  };

  return (
    <div className={styles.editor}>
      <label className={styles.field}>
        <span className={styles.label}>Name</span>
        <input
          className={styles.input}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </label>

      <label className={styles.field}>
        <span className={styles.label}>Bucket</span>
        <select
          className={styles.input}
          value={bucketId}
          onChange={(event) => setBucketId(Number(event.target.value))}
        >
          {buckets.map((bucket) => (
            <option key={bucket.id} value={bucket.id}>
              {bucket.name}
            </option>
          ))}
        </select>
      </label>

      <div className={styles.field}>
        <span className={styles.label}>Scheduled on</span>
        <WeekdayPicker value={weekdays} onChange={setWeekdays} />
      </div>

      <label className={styles.field}>
        <span className={styles.label}>Time cap (minutes, optional)</span>
        <input
          className={styles.input}
          inputMode="numeric"
          value={cap}
          onChange={(event) => setCap(event.target.value.replace(/\D/g, ""))}
        />
      </label>

      <label className={styles.checkRow}>
        <input
          type="checkbox"
          checked={anytime}
          onChange={(event) => setAnytime(event.target.checked)}
        />
        <span>
          Any time of day
          <span className={styles.hint}>Sorts to the end of the list.</span>
        </span>
      </label>

      <label className={styles.checkRow}>
        <input
          type="checkbox"
          checked={seasonal}
          onChange={(event) => setSeasonal(event.target.checked)}
        />
        <span>
          Only in season
          <span className={styles.hint}>Hidden entirely when your season is off.</span>
        </span>
      </label>

      <div className={styles.editorActions}>
        <button type="button" className={styles.primary} onClick={() => void save()}>
          Save
        </button>
        <button type="button" className={styles.textButton} onClick={onDone}>
          Cancel
        </button>
        <button
          type="button"
          className={styles.archiveButton}
          onClick={() => {
            if (!window.confirm(`Archive "${habit.name}"? Its history is kept.`)) return;
            archive.mutate(habit.id, {
              onSuccess: onDone,
              onError: () => onNotice("Couldn't archive that."),
            });
          }}
        >
          Archive
        </button>
      </div>
      <p className={styles.hint}>
        Archiving removes it from future days. Everything it recorded stays in your
        week and month views.
      </p>
    </div>
  );
}

function NewHabitForm({
  buckets,
  nextSortOrder,
  onNotice,
}: {
  buckets: BucketOut[];
  nextSortOrder: number;
  onNotice: (message: string) => void;
}) {
  const createHabit = useCreateHabit();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [bucketId, setBucketId] = useState(buckets[0]?.id ?? 0);
  const [weekdays, setWeekdays] = useState<number[]>([0, 1, 2, 3, 4, 5, 6]);

  if (!open) {
    return (
      <button type="button" className={styles.addButton} onClick={() => setOpen(true)}>
        + Add a habit
      </button>
    );
  }

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!name.trim() || !bucketId) return;
    createHabit.mutate(
      {
        bucket_id: bucketId,
        name: name.trim(),
        target_per_week: weekdays.length,
        weekdays,
        sort_order: nextSortOrder,
      },
      {
        onSuccess: () => {
          setName("");
          setOpen(false);
        },
        onError: () => onNotice("Couldn't add that habit."),
      },
    );
  };

  return (
    <form className={styles.editor} onSubmit={submit}>
      <label className={styles.field}>
        <span className={styles.label}>Name</span>
        <input
          className={styles.input}
          value={name}
          autoFocus
          onChange={(event) => setName(event.target.value)}
          placeholder="e.g. Morning walk"
        />
      </label>

      <label className={styles.field}>
        <span className={styles.label}>Bucket</span>
        <select
          className={styles.input}
          value={bucketId}
          onChange={(event) => setBucketId(Number(event.target.value))}
        >
          {buckets.map((bucket) => (
            <option key={bucket.id} value={bucket.id}>
              {bucket.name}
            </option>
          ))}
        </select>
      </label>

      <div className={styles.field}>
        <span className={styles.label}>Scheduled on</span>
        <WeekdayPicker value={weekdays} onChange={setWeekdays} />
      </div>

      <div className={styles.editorActions}>
        <button type="submit" className={styles.primary} disabled={!name.trim()}>
          Add habit
        </button>
        <button type="button" className={styles.textButton} onClick={() => setOpen(false)}>
          Cancel
        </button>
      </div>
    </form>
  );
}

function BucketManager({ onNotice }: { onNotice: (message: string) => void }) {
  const { data: buckets } = useBuckets();
  const createBucket = useCreateBucket();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [colour, setColour] = useState("#CA758A");

  return (
    <section className={styles.section}>
      <h2 className={styles.sectionHeading}>Buckets</h2>
      <ul className={styles.bucketList}>
        {(buckets ?? []).map((bucket) => (
          <li key={bucket.id} className={styles.bucketChip}>
            <span className={styles.swatch} style={{ background: bucket.color_hex }} />
            {bucket.name}
          </li>
        ))}
      </ul>

      {open ? (
        <form
          className={styles.editor}
          onSubmit={(event) => {
            event.preventDefault();
            if (!name.trim()) return;
            createBucket.mutate(
              { name: name.trim(), color_hex: colour, sort_order: (buckets?.length ?? 0) + 1 },
              {
                onSuccess: () => {
                  setName("");
                  setOpen(false);
                },
                onError: () => onNotice("Couldn't add that bucket."),
              },
            );
          }}
        >
          <label className={styles.field}>
            <span className={styles.label}>Name</span>
            <input
              className={styles.input}
              value={name}
              autoFocus
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label className={styles.field}>
            <span className={styles.label}>Colour</span>
            <input
              type="color"
              className={styles.colourInput}
              value={colour}
              onChange={(event) => setColour(event.target.value)}
            />
          </label>
          <div className={styles.editorActions}>
            <button type="submit" className={styles.primary}>
              Add bucket
            </button>
            <button type="button" className={styles.textButton} onClick={() => setOpen(false)}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <button type="button" className={styles.addButton} onClick={() => setOpen(true)}>
          + Add a bucket
        </button>
      )}
    </section>
  );
}

export function Habits() {
  const { data: habits, isPending } = useHabits();
  const { data: buckets } = useBuckets();
  const reorder = useReorderHabits();
  const [editing, setEditing] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  if (isPending || !habits || !buckets) {
    return <p className={styles.quiet}>Loading…</p>;
  }

  const move = (index: number, delta: number) => {
    const target = index + delta;
    if (target < 0 || target >= habits.length) return;

    // Renumber the whole list so positions stay unambiguous after a swap.
    const reordered = [...habits];
    const [moved] = reordered.splice(index, 1);
    reordered.splice(target, 0, moved);

    reorder.mutate(
      reordered.map((habit, position) => ({
        habit_id: habit.id,
        sort_order: position + 1,
      })),
      { onError: () => setNotice("Couldn't reorder just now.") },
    );
  };

  return (
    <div>
      <Link to="/settings" className={styles.back}>
        ‹ Settings
      </Link>
      <h1 className={styles.heading}>Habits</h1>

      {habits.length === 0 ? (
        <p className={styles.empty}>
          Your board is empty. Add a bucket first, then start adding habits —
          they'll appear on Today from tomorrow's schedule onward.
        </p>
      ) : null}

      <ul className={styles.habitList}>
        {habits.map((habit, index) => (
          <li key={habit.id} className={styles.habitItem}>
            <div className={styles.habitRow}>
              <span className={styles.reorder}>
                <button
                  type="button"
                  className={styles.reorderButton}
                  onClick={() => move(index, -1)}
                  disabled={index === 0}
                  aria-label={`Move ${habit.name} up`}
                >
                  ▲
                </button>
                <button
                  type="button"
                  className={styles.reorderButton}
                  onClick={() => move(index, 1)}
                  disabled={index === habits.length - 1}
                  aria-label={`Move ${habit.name} down`}
                >
                  ▼
                </button>
              </span>

              <button
                type="button"
                className={styles.habitMain}
                onClick={() => setEditing(editing === habit.id ? null : habit.id)}
                aria-expanded={editing === habit.id}
              >
                <span className={styles.habitName}>{habit.name}</span>
                <span className={styles.habitDays}>
                  {habit.weekdays.length === 7
                    ? "Every day"
                    : habit.weekdays.map((day) => WEEKDAYS[day]).join(" · ") || "Not scheduled"}
                  {habit.anytime ? " · any time" : ""}
                  {habit.season_dependent ? " · in season" : ""}
                </span>
              </button>
            </div>

            {editing === habit.id ? (
              <HabitEditor
                habit={habit}
                buckets={buckets}
                onDone={() => setEditing(null)}
                onNotice={setNotice}
              />
            ) : null}
          </li>
        ))}
      </ul>

      <NewHabitForm
        buckets={buckets}
        nextSortOrder={habits.length + 1}
        onNotice={setNotice}
      />

      <BucketManager onNotice={setNotice} />

      <Notice message={notice} onDismiss={() => setNotice(null)} />
    </div>
  );
}
