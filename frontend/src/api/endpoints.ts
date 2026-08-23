/** Typed wrappers over each API endpoint. One function per operation. */

import { request } from "./client";
import type {
  BucketOut,
  CompletionBody,
  DayDetailView,
  DayView,
  HabitOut,
  LoginResponse,
  MeResponse,
  MonthView,
  TodayView,
  UserSummary,
  WeekView,
} from "./types";

// --- Auth -----------------------------------------------------------------

export const listUsers = (): Promise<UserSummary[]> =>
  request<UserSummary[]>("/users", { anonymous: true });

export const login = (user_id: number, pin: string): Promise<LoginResponse> =>
  request<LoginResponse>("/auth/login", {
    method: "POST",
    body: { user_id, pin },
    anonymous: true,
  });

export const logout = (): Promise<void> =>
  request<void>("/auth/logout", { method: "POST" });

// --- Board reads ----------------------------------------------------------

export const getToday = (): Promise<TodayView> => request<TodayView>("/today");

export const getDay = (date: string): Promise<DayDetailView> =>
  request<DayDetailView>(`/days/${date}`);

export const getWeek = (containingDate?: string): Promise<WeekView> =>
  request<WeekView>(
    containingDate ? `/weeks?containing_date=${containingDate}` : "/weeks",
  );

export const getMonth = (year: number, month: number): Promise<MonthView> =>
  request<MonthView>(`/months/${year}/${month}`);

// --- Completions ----------------------------------------------------------

export const complete = (body: CompletionBody): Promise<DayView> =>
  request<DayView>("/completions", { method: "POST", body });

export const uncomplete = (body: CompletionBody): Promise<DayView> =>
  request<DayView>("/completions", { method: "DELETE", body });

export const addBonus = (body: CompletionBody): Promise<DayView> =>
  request<DayView>("/completions/bonus", { method: "POST", body });

// --- Settings -------------------------------------------------------------

export const getMe = (): Promise<MeResponse> => request<MeResponse>("/me");

export interface MePatch {
  display_name?: string;
  timezone?: string;
  season_active?: boolean;
}

export const patchMe = (body: MePatch): Promise<MeResponse> =>
  request<MeResponse>("/me", { method: "PATCH", body });

export const changePin = (current_pin: string, new_pin: string): Promise<MeResponse> =>
  request<MeResponse>("/me/pin", {
    method: "PUT",
    body: { current_pin, new_pin },
  });

// --- Buckets --------------------------------------------------------------

export const listBuckets = (): Promise<BucketOut[]> => request<BucketOut[]>("/buckets");

export interface BucketBody {
  name: string;
  color_hex: string;
  sort_order?: number;
}

export const createBucket = (body: BucketBody): Promise<BucketOut> =>
  request<BucketOut>("/buckets", { method: "POST", body });

export const updateBucket = (
  id: number,
  body: Partial<BucketBody>,
): Promise<BucketOut> =>
  request<BucketOut>(`/buckets/${id}`, { method: "PATCH", body });

// --- Habits ---------------------------------------------------------------

export const listHabits = (includeArchived = false): Promise<HabitOut[]> =>
  request<HabitOut[]>(`/habits${includeArchived ? "?include_archived=true" : ""}`);

export interface HabitBody {
  bucket_id: number;
  name: string;
  target_per_week: number;
  weekdays: number[];
  sort_order?: number;
  time_cap_minutes?: number | null;
  season_dependent?: boolean;
  anytime?: boolean;
}

export const createHabit = (body: HabitBody): Promise<HabitOut> =>
  request<HabitOut>("/habits", { method: "POST", body });

export interface HabitPatch {
  bucket_id?: number;
  name?: string;
  target_per_week?: number;
  time_cap_minutes?: number | null;
  season_dependent?: boolean;
  sort_order?: number;
  anytime?: boolean;
  clear_time_cap?: boolean;
}

export const updateHabit = (id: number, body: HabitPatch): Promise<HabitOut> =>
  request<HabitOut>(`/habits/${id}`, { method: "PATCH", body });

export const setSchedule = (id: number, weekdays: number[]): Promise<HabitOut> =>
  request<HabitOut>(`/habits/${id}/schedule`, { method: "PUT", body: { weekdays } });

export const archiveHabit = (id: number): Promise<HabitOut> =>
  request<HabitOut>(`/habits/${id}/archive`, { method: "POST" });

export const reorderHabits = (
  ordering: { habit_id: number; sort_order: number }[],
): Promise<HabitOut[]> =>
  request<HabitOut[]>("/habits/reorder", { method: "PATCH", body: ordering });
