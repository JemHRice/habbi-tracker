/**
 * Tracking — for looking back, not for ticking.
 *
 * Weekly is a calm glance at each day. Monthly is richer: how each habit went,
 * stated factually, above a calendar you can tap into.
 *
 * Nothing on this screen is red, ranked, or sorted worst-first. A habit that
 * slipped gets exactly the same treatment as one that stuck — the numbers are
 * there to be looked at, not to be answered for.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useMonth, useWeek } from "../api/queries";
import type { MonthDayView, MonthHabitRate, WeekDayView } from "../api/types";
import { Habbi } from "../components/Habbi";
import styles from "./Tracking.module.css";

const DAY_INITIALS = ["M", "T", "W", "T", "F", "S", "S"];

function percentLabel(pct: number | null): string {
  return pct === null ? "—" : `${Math.round(pct * 100)}%`;
}

/** Fill strength for a day cell. Always rose; only the opacity varies. */
function fillStyle(pct: number | null): React.CSSProperties {
  if (pct === null || pct === 0) return {};
  return { background: `color-mix(in srgb, var(--rose) ${Math.round(pct * 100)}%, var(--rose-soft))` };
}

function WeekPanel() {
  const { data, isPending, isError } = useWeek();

  if (isPending) return <p className={styles.quiet}>Loading your week…</p>;
  if (isError || !data) return <p className={styles.quiet}>We couldn't load your week.</p>;

  return (
    <section aria-label="This week">
      <ul className={styles.weekList}>
        {data.days.map((day: WeekDayView) => (
          <li
            key={day.date}
            className={[styles.weekDay, day.locked_empty ? styles.crossed : ""]
              .filter(Boolean)
              .join(" ")}
          >
            <span className={styles.weekDayName}>{DAY_INITIALS[day.weekday]}</span>
            <span className={styles.weekBarTrack}>
              <span
                className={styles.weekBarFill}
                style={{ width: `${(day.pct ?? 0) * 100}%` }}
              />
            </span>
            <span className={styles.weekPct}>
              {day.locked_empty ? "no data" : percentLabel(day.pct)}
            </span>
          </li>
        ))}
      </ul>
      <p className={styles.footnote}>
        A crossed-out day is one with nothing recorded. That's all it means.
      </p>
    </section>
  );
}

function HabitRates({ habits }: { habits: MonthHabitRate[] }) {
  if (habits.length === 0) {
    return <p className={styles.quiet}>Nothing recorded this month yet.</p>;
  }

  return (
    <ul className={styles.rateList}>
      {habits.map((row) => (
        <li key={row.habit_id} className={styles.rateRow}>
          <span className={styles.rateName}>{row.name}</span>
          <span className={styles.rateTrack}>
            <span
              className={styles.rateFill}
              style={{
                width: `${(row.rate ?? 0) * 100}%`,
                background: row.bucket_color_hex,
              }}
            />
          </span>
          <span className={styles.rateCount}>
            {row.completed_days}/{row.scheduled_days}
          </span>
        </li>
      ))}
    </ul>
  );
}

function MonthPanel() {
  const navigate = useNavigate();
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);

  const { data, isPending, isError } = useMonth(year, month);

  const step = (delta: number) => {
    const next = new Date(year, month - 1 + delta, 1);
    setYear(next.getFullYear());
    setMonth(next.getMonth() + 1);
  };

  const monthName = new Date(year, month - 1, 1).toLocaleDateString(undefined, {
    month: "long",
    year: "numeric",
  });

  // Monday-first grid, so the leading blanks depend on the 1st's weekday.
  const leadingBlanks = data ? (new Date(`${data.days[0].date}T00:00:00`).getDay() + 6) % 7 : 0;

  return (
    <section aria-label="This month">
      <div className={styles.monthNav}>
        <button type="button" className={styles.navButton} onClick={() => step(-1)}>
          ‹<span className="sr-only">Previous month</span>
        </button>
        <h2 className={styles.monthName}>{monthName}</h2>
        <button type="button" className={styles.navButton} onClick={() => step(1)}>
          ›<span className="sr-only">Next month</span>
        </button>
      </div>

      {isPending ? <p className={styles.quiet}>Loading…</p> : null}
      {isError ? <p className={styles.quiet}>We couldn't load this month.</p> : null}

      {data ? (
        <>
          <h3 className={styles.sectionHeading}>How it went</h3>
          <HabitRates habits={data.habits} />

          <h3 className={styles.sectionHeading}>Calendar</h3>
          <div className={styles.calendarHead} aria-hidden="true">
            {DAY_INITIALS.map((initial, index) => (
              <span key={index}>{initial}</span>
            ))}
          </div>
          <div className={styles.calendar}>
            {Array.from({ length: leadingBlanks }, (_, index) => (
              <span key={`blank-${index}`} />
            ))}
            {data.days.map((day: MonthDayView) => (
              <button
                key={day.date}
                type="button"
                className={styles.calendarDay}
                style={fillStyle(day.pct)}
                onClick={() => navigate(`/days/${day.date}`)}
                aria-label={`${day.date}, ${day.no_data ? "no data" : percentLabel(day.pct)}`}
              >
                {day.no_data ? (
                  <Habbi pose="oops" size={26} />
                ) : (
                  <span className={styles.calendarNumber}>
                    {Number(day.date.slice(-2))}
                  </span>
                )}
              </button>
            ))}
          </div>
          <p className={styles.footnote}>
            Habbi marks a day with nothing recorded. Tap any day for its detail.
          </p>
        </>
      ) : null}
    </section>
  );
}

export function Tracking() {
  const [panel, setPanel] = useState<"week" | "month">("week");

  return (
    <div>
      <h1 className={styles.heading}>Tracking</h1>

      <div className={styles.tabs} role="tablist">
        {(["week", "month"] as const).map((option) => (
          <button
            key={option}
            type="button"
            role="tab"
            aria-selected={panel === option}
            className={[styles.tab, panel === option ? styles.tabActive : ""]
              .filter(Boolean)
              .join(" ")}
            onClick={() => setPanel(option)}
          >
            {option === "week" ? "Weekly" : "Monthly"}
          </button>
        ))}
      </div>

      {panel === "week" ? <WeekPanel /> : <MonthPanel />}
    </div>
  );
}
