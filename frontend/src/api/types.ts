/**
 * Types mirroring the Phase 2 API. The backend is the source of truth for all
 * of these shapes; `/docs` is the contract.
 *
 * Percentages are fractions from 0 to 1, or `null` when nothing was scheduled
 * — a rest day, which is not the same thing as zero.
 */

export interface HabitRef {
  id: number;
  name: string;
  bucket_id: number;
  bucket_name: string;
  bucket_color_hex: string;
  sort_order: number;
  anytime: boolean;
  time_cap_minutes: number | null;
  season_dependent: boolean;
}

export interface CompletedEntry {
  habit: HabitRef;
  completed_at: string;
  is_bonus: boolean;
}

export interface TodayView {
  kind: "today";
  date: string;
  editable: boolean;
  active: HabitRef[];
  completed: CompletedEntry[];
  daily_pct: number | null;
  done_count: number;
  remaining_count: number;
  available_extras: HabitRef[];
  bonuses: CompletedEntry[];
}

export interface DayDetailView {
  kind: "day";
  date: string;
  editable: boolean;
  completed: CompletedEntry[];
  not_completed: HabitRef[];
  bonuses: CompletedEntry[];
  final_pct: number | null;
  no_data: boolean;
}

/** Whichever view matches the date a mutation touched. Discriminate on `kind`. */
export type DayView = TodayView | DayDetailView;

export interface WeekDayView {
  date: string;
  weekday: number;
  pct: number | null;
  scheduled_count: number;
  done_count: number;
  editable: boolean;
  locked_empty: boolean;
}

export interface WeekView {
  week_start: string;
  week_end: string;
  days: WeekDayView[];
}

export interface MonthHabitRate {
  habit_id: number;
  name: string;
  bucket_name: string;
  bucket_color_hex: string;
  scheduled_days: number;
  completed_days: number;
  rate: number | null;
}

export interface MonthDayView {
  date: string;
  pct: number | null;
  no_data: boolean;
}

export interface MonthView {
  year: number;
  month: number;
  habits: MonthHabitRate[];
  days: MonthDayView[];
}

export interface UserSummary {
  id: number;
  display_name: string;
}

export interface LoginResponse {
  token: string;
  expires_at: string;
  must_change_pin: boolean;
}

export interface MeResponse {
  display_name: string;
  timezone: string;
  season_active: boolean;
  reminders_enabled: boolean;
  must_change_pin: boolean;
}

export interface BucketOut {
  id: number;
  name: string;
  color_hex: string;
  sort_order: number;
}

export interface HabitOut {
  id: number;
  bucket_id: number;
  name: string;
  target_per_week: number;
  time_cap_minutes: number | null;
  season_dependent: boolean;
  sort_order: number;
  anytime: boolean;
  active: boolean;
  archived_at: string | null;
  weekdays: number[];
}

/** The codes the API's error envelope can carry. */
export type ApiErrorCode =
  | "UNAUTHENTICATED"
  | "PIN_INVALID"
  | "PIN_THROTTLED"
  | "EDIT_WINDOW_LOCKED"
  | "NOT_FOUND"
  | "VALIDATION"
  | "OFFLINE";

export interface CompletionBody {
  habit_id: number;
  date: string;
}
