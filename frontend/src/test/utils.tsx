/** Helpers for rendering components with the providers they expect. */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";

import type { HabitRef, TodayView } from "../api/types";

/** A client with retries off, so a failure surfaces immediately in a test. */
export function testQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity },
      mutations: { retry: false },
    },
  });
}

export function renderWithProviders(
  ui: ReactElement,
  client: QueryClient = testQueryClient(),
) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );

  return { ...render(ui, { wrapper }), client };
}

let nextId = 1;

export function habit(overrides: Partial<HabitRef> = {}): HabitRef {
  const id = overrides.id ?? nextId++;
  return {
    id,
    name: `Habit ${id}`,
    bucket_id: 1,
    bucket_name: "Self-care",
    bucket_color_hex: "#CA758A",
    sort_order: id,
    anytime: false,
    time_cap_minutes: null,
    season_dependent: false,
    ...overrides,
  };
}

export function todayView(overrides: Partial<TodayView> = {}): TodayView {
  const active = overrides.active ?? [];
  const completed = overrides.completed ?? [];
  const scheduledDone = completed.filter((entry) => !entry.is_bonus).length;
  const total = active.length + scheduledDone;

  return {
    kind: "today",
    date: "2026-03-16",
    editable: true,
    active,
    completed,
    daily_pct: total === 0 ? null : scheduledDone / total,
    done_count: scheduledDone,
    remaining_count: active.length,
    available_extras: [],
    bonuses: completed.filter((entry) => entry.is_bonus),
    ...overrides,
  };
}
