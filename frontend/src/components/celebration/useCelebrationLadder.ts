/**
 * Decides when to celebrate.
 *
 * Three rungs, all encouraging: halfway, last-one-left, and the whole day done.
 * There is no rung for falling behind, and no code path here can produce one.
 *
 * Celebrations fire on the *transition* — the moment you tick something — never
 * on load. Opening the app onto a half-finished day should feel like picking up
 * where you left off, not like being congratulated for arriving.
 */

import { useEffect, useRef, useState } from "react";

import type { TodayView } from "../../api/types";

export type CelebrationTier = "halfway" | "lastOne" | "complete";

function tierFor(done: number, remaining: number): CelebrationTier | null {
  const total = done + remaining;
  if (total === 0) return null;
  if (remaining === 0) return "complete";
  if (remaining === 1) return "lastOne";
  // Halfway lands on the tick that reaches the halfway mark, not past it.
  if (done > 0 && done === Math.ceil(total / 2)) return "halfway";
  return null;
}

export function useCelebrationLadder(view: TodayView | undefined) {
  const [tier, setTier] = useState<CelebrationTier | null>(null);
  const previousDone = useRef<number | null>(null);
  const currentDate = useRef<string | null>(null);

  useEffect(() => {
    if (!view) return;

    // A new day resets the baseline without celebrating anything.
    if (currentDate.current !== view.date) {
      currentDate.current = view.date;
      previousDone.current = view.done_count;
      return;
    }

    const before = previousDone.current;
    previousDone.current = view.done_count;

    // Only a fresh completion celebrates. Un-ticking never does.
    if (before === null || view.done_count <= before) return;

    setTier(tierFor(view.done_count, view.remaining_count));
  }, [view]);

  return { tier, dismiss: () => setTier(null) };
}

export const __testing = { tierFor };
