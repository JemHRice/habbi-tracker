/**
 * The optimistic predictions must agree with the backend's rules, especially
 * the one that matters most: a bonus never moves the percentage.
 */

import { describe, expect, it } from "vitest";

import {
  bonusInToday,
  completeInToday,
  uncompleteInToday,
} from "./optimistic";
import { habit, todayView } from "../test/utils";

const AT = "2026-03-16T07:00:00Z";

describe("completing a habit", () => {
  it("moves it to the pile and advances the percentage", () => {
    const shower = habit({ id: 1, name: "Shower" });
    const view = todayView({ active: [shower, habit({ id: 2 })] });

    const next = completeInToday(view, 1, AT);

    expect(next.active.map((entry) => entry.id)).toEqual([2]);
    expect(next.completed.map((entry) => entry.habit.name)).toEqual(["Shower"]);
    expect(next.done_count).toBe(1);
    expect(next.remaining_count).toBe(1);
    expect(next.daily_pct).toBe(0.5);
  });

  it("reaches exactly 1 when the last one is ticked, never more", () => {
    const view = todayView({ active: [habit({ id: 1 })] });

    const next = completeInToday(view, 1, AT);

    expect(next.daily_pct).toBe(1);
    expect(next.remaining_count).toBe(0);
  });

  it("ignores a habit that isn't on the active list", () => {
    const view = todayView({ active: [habit({ id: 1 })] });

    expect(completeInToday(view, 99, AT)).toBe(view);
  });
});

describe("un-ticking", () => {
  it("restores the habit to its place in display order", () => {
    const first = habit({ id: 1, sort_order: 1 });
    const second = habit({ id: 2, sort_order: 2 });
    const third = habit({ id: 3, sort_order: 3 });
    const view = completeInToday(
      todayView({ active: [first, second, third] }),
      2,
      AT,
    );

    const next = uncompleteInToday(view, 2);

    expect(next.active.map((entry) => entry.id)).toEqual([1, 2, 3]);
    expect(next.completed).toHaveLength(0);
    expect(next.done_count).toBe(0);
  });

  it("puts anytime habits back at the end regardless of sort order", () => {
    const timed = habit({ id: 1, sort_order: 9, anytime: false });
    const whenever = habit({ id: 2, sort_order: 1, anytime: true });
    const view = completeInToday(todayView({ active: [timed, whenever] }), 2, AT);

    const next = uncompleteInToday(view, 2);

    expect(next.active.map((entry) => entry.id)).toEqual([1, 2]);
  });
});

describe("bonuses", () => {
  it("joins the completed pile without touching the percentage", () => {
    const extra = habit({ id: 5, name: "Laundry" });
    const view = todayView({
      active: [habit({ id: 1 }), habit({ id: 2 })],
      available_extras: [extra],
    });

    const next = bonusInToday(view, 5, AT);

    expect(next.completed.map((entry) => entry.habit.name)).toEqual(["Laundry"]);
    expect(next.bonuses).toHaveLength(1);
    expect(next.done_count).toBe(view.done_count);
    expect(next.remaining_count).toBe(view.remaining_count);
    expect(next.daily_pct).toBe(view.daily_pct);
  });

  it("cannot push a finished day past 100%", () => {
    const extra = habit({ id: 5 });
    const done = completeInToday(
      todayView({ active: [habit({ id: 1 })], available_extras: [extra] }),
      1,
      AT,
    );

    const next = bonusInToday(done, 5, AT);

    expect(next.daily_pct).toBe(1);
  });

  it("leaves the extras picker once logged, and returns if undone", () => {
    const extra = habit({ id: 5 });
    const view = bonusInToday(
      todayView({ active: [habit({ id: 1 })], available_extras: [extra] }),
      5,
      AT,
    );
    expect(view.available_extras).toHaveLength(0);

    const undone = uncompleteInToday(view, 5);

    expect(undone.available_extras.map((entry) => entry.id)).toEqual([5]);
    expect(undone.bonuses).toHaveLength(0);
    expect(undone.done_count).toBe(view.done_count);
  });
});

describe("a rest day", () => {
  it("has no percentage at all rather than zero", () => {
    expect(todayView({ active: [] }).daily_pct).toBeNull();
  });
});
