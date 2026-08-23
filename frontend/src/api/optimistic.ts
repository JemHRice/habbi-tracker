/**
 * Local predictions of what a tick will do, applied before the server answers.
 *
 * These mirror the backend's rules exactly — most importantly that **bonuses
 * never move the percentage**. If these ever disagree with the server, the
 * server wins: every mutation replaces the cache with the response it returns.
 *
 * Kept pure and separate from the query hooks so the rules can be tested
 * directly, without a network or a React tree.
 */

import type { CompletedEntry, DayDetailView, HabitRef, TodayView } from "./types";

/** Timed habits first in hand-set order, then the ones with no natural time. */
function byDisplayOrder(a: HabitRef, b: HabitRef): number {
  if (a.anytime !== b.anytime) return a.anytime ? 1 : -1;
  if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order;
  return a.id - b.id;
}

function entry(habit: HabitRef, isBonus: boolean, at: string): CompletedEntry {
  return { habit, completed_at: at, is_bonus: isBonus };
}

/** Completed-scheduled over total-scheduled. Null when nothing is scheduled. */
function fraction(done: number, total: number): number | null {
  if (total === 0) return null;
  return done / total;
}

// --- Today ----------------------------------------------------------------

export function completeInToday(
  view: TodayView,
  habitId: number,
  at: string = new Date().toISOString(),
): TodayView {
  const habit = view.active.find((candidate) => candidate.id === habitId);
  if (!habit) return view;

  const done = view.done_count + 1;
  const total = view.done_count + view.remaining_count;

  return {
    ...view,
    active: view.active.filter((candidate) => candidate.id !== habitId),
    completed: [...view.completed, entry(habit, false, at)],
    done_count: done,
    remaining_count: view.remaining_count - 1,
    daily_pct: fraction(done, total),
  };
}

export function uncompleteInToday(view: TodayView, habitId: number): TodayView {
  const found = view.completed.find((candidate) => candidate.habit.id === habitId);
  if (!found) return view;

  const completed = view.completed.filter((candidate) => candidate.habit.id !== habitId);

  // Un-ticking a bonus removes a row that was never counted, so the numbers
  // stay put and the habit returns to the extras picker.
  if (found.is_bonus) {
    return {
      ...view,
      completed,
      bonuses: view.bonuses.filter((candidate) => candidate.habit.id !== habitId),
      available_extras: [...view.available_extras, found.habit].sort(byDisplayOrder),
    };
  }

  const done = view.done_count - 1;
  const total = view.done_count + view.remaining_count;

  return {
    ...view,
    active: [...view.active, found.habit].sort(byDisplayOrder),
    completed,
    done_count: done,
    remaining_count: view.remaining_count + 1,
    daily_pct: fraction(done, total),
  };
}

export function bonusInToday(
  view: TodayView,
  habitId: number,
  at: string = new Date().toISOString(),
): TodayView {
  const habit = view.available_extras.find((candidate) => candidate.id === habitId);
  if (!habit) return view;

  const added = entry(habit, true, at);

  // Deliberately leaves done_count, remaining_count and daily_pct untouched.
  return {
    ...view,
    available_extras: view.available_extras.filter(
      (candidate) => candidate.id !== habitId,
    ),
    completed: [...view.completed, added],
    bonuses: [...view.bonuses, added],
  };
}

// --- A single past day ----------------------------------------------------

function scheduledTotals(view: DayDetailView): { done: number; total: number } {
  const done = view.completed.filter((candidate) => !candidate.is_bonus).length;
  return { done, total: done + view.not_completed.length };
}

export function completeInDay(
  view: DayDetailView,
  habitId: number,
  at: string = new Date().toISOString(),
): DayDetailView {
  const habit = view.not_completed.find((candidate) => candidate.id === habitId);
  if (!habit) return view;

  const { done, total } = scheduledTotals(view);

  return {
    ...view,
    not_completed: view.not_completed.filter((candidate) => candidate.id !== habitId),
    completed: [...view.completed, entry(habit, false, at)],
    final_pct: fraction(done + 1, total),
    no_data: false,
  };
}

export function uncompleteInDay(view: DayDetailView, habitId: number): DayDetailView {
  const found = view.completed.find((candidate) => candidate.habit.id === habitId);
  if (!found) return view;

  const completed = view.completed.filter((candidate) => candidate.habit.id !== habitId);
  const { done, total } = scheduledTotals(view);

  if (found.is_bonus) {
    return {
      ...view,
      completed,
      bonuses: view.bonuses.filter((candidate) => candidate.habit.id !== habitId),
    };
  }

  return {
    ...view,
    completed,
    not_completed: [...view.not_completed, found.habit].sort(byDisplayOrder),
    final_pct: fraction(done - 1, total),
  };
}

export function bonusInDay(
  view: DayDetailView,
  habit: HabitRef,
  at: string = new Date().toISOString(),
): DayDetailView {
  const added = entry(habit, true, at);
  return {
    ...view,
    completed: [...view.completed, added],
    bonuses: [...view.bonuses, added],
    no_data: false,
  };
}
