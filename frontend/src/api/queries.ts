/** TanStack Query hooks. Every server interaction the app makes goes through here. */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
} from "@tanstack/react-query";

import * as api from "./endpoints";
import {
  bonusInDay,
  bonusInToday,
  completeInDay,
  completeInToday,
  uncompleteInDay,
  uncompleteInToday,
} from "./optimistic";
import type {
  BucketOut,
  CompletionBody,
  DayDetailView,
  DayView,
  HabitOut,
  HabitRef,
  MeResponse,
  MonthView,
  TodayView,
  WeekView,
} from "./types";

export const queryKeys = {
  users: ["users"] as const,
  today: ["today"] as const,
  day: (date: string) => ["day", date] as const,
  week: (containingDate?: string) => ["week", containingDate ?? "current"] as const,
  month: (year: number, month: number) => ["month", year, month] as const,
  me: ["me"] as const,
  habits: (includeArchived: boolean) => ["habits", includeArchived] as const,
  buckets: ["buckets"] as const,
};

// --- Reads ----------------------------------------------------------------

export const useUsers = () =>
  useQuery({ queryKey: queryKeys.users, queryFn: api.listUsers });

export const useToday = () =>
  useQuery({ queryKey: queryKeys.today, queryFn: api.getToday });

export const useDay = (date: string) =>
  useQuery({ queryKey: queryKeys.day(date), queryFn: () => api.getDay(date) });

export const useWeek = (containingDate?: string) =>
  useQuery({
    queryKey: queryKeys.week(containingDate),
    queryFn: () => api.getWeek(containingDate),
  });

export const useMonth = (year: number, month: number) =>
  useQuery({
    queryKey: queryKeys.month(year, month),
    queryFn: () => api.getMonth(year, month),
  });

export const useMe = () => useQuery({ queryKey: queryKeys.me, queryFn: api.getMe });

export const useHabits = (includeArchived = false) =>
  useQuery({
    queryKey: queryKeys.habits(includeArchived),
    queryFn: () => api.listHabits(includeArchived),
  });

export const useBuckets = () =>
  useQuery({ queryKey: queryKeys.buckets, queryFn: api.listBuckets });

// --- Completions ----------------------------------------------------------

interface Snapshot {
  today?: TodayView;
  day?: DayDetailView;
}

type Predictor = (
  snapshot: Snapshot,
  variables: CompletionBody & { habit?: HabitRef },
) => Snapshot;

/**
 * Build a completion mutation with optimistic updating.
 *
 * The flow is the standard one: predict locally, roll back on failure, and
 * replace with the server's answer on success — which is why the mutation
 * endpoints return the live view of the date they changed.
 */
function useCompletionMutation(
  mutationFn: (body: CompletionBody) => Promise<DayView>,
  predict: Predictor,
): UseMutationResult<DayView, Error, CompletionBody & { habit?: HabitRef }> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ habit_id, date }) => mutationFn({ habit_id, date }),

    onMutate: async (variables) => {
      await Promise.all([
        queryClient.cancelQueries({ queryKey: queryKeys.today }),
        queryClient.cancelQueries({ queryKey: queryKeys.day(variables.date) }),
      ]);

      const snapshot: Snapshot = {
        today: queryClient.getQueryData<TodayView>(queryKeys.today),
        day: queryClient.getQueryData<DayDetailView>(queryKeys.day(variables.date)),
      };

      const predicted = predict(snapshot, variables);

      if (predicted.today && snapshot.today?.date === variables.date) {
        queryClient.setQueryData(queryKeys.today, predicted.today);
      }
      if (predicted.day) {
        queryClient.setQueryData(queryKeys.day(variables.date), predicted.day);
      }

      return snapshot;
    },

    onError: (_error, variables, snapshot) => {
      if (!snapshot) return;
      if (snapshot.today) queryClient.setQueryData(queryKeys.today, snapshot.today);
      if (snapshot.day) {
        queryClient.setQueryData(queryKeys.day(variables.date), snapshot.day);
      }
    },

    onSuccess: (result, variables) => {
      if (result.kind === "today") {
        queryClient.setQueryData(queryKeys.today, result);
      }
      queryClient.setQueryData(
        queryKeys.day(variables.date),
        result.kind === "day" ? result : undefined,
      );
    },

    onSettled: () => {
      // Week and month rollups changed too, but nothing is looking at them
      // right now, so mark them stale rather than refetching eagerly.
      queryClient.invalidateQueries({ queryKey: ["week"] });
      queryClient.invalidateQueries({ queryKey: ["month"] });
    },
  });
}

export const useComplete = () =>
  useCompletionMutation(api.complete, (snapshot, variables) => ({
    today: snapshot.today && completeInToday(snapshot.today, variables.habit_id),
    day: snapshot.day && completeInDay(snapshot.day, variables.habit_id),
  }));

export const useUncomplete = () =>
  useCompletionMutation(api.uncomplete, (snapshot, variables) => ({
    today: snapshot.today && uncompleteInToday(snapshot.today, variables.habit_id),
    day: snapshot.day && uncompleteInDay(snapshot.day, variables.habit_id),
  }));

export const useAddBonus = () =>
  useCompletionMutation(api.addBonus, (snapshot, variables) => ({
    today: snapshot.today && bonusInToday(snapshot.today, variables.habit_id),
    day:
      snapshot.day && variables.habit
        ? bonusInDay(snapshot.day, variables.habit)
        : snapshot.day,
  }));

// --- Settings & management ------------------------------------------------

export const usePatchMe = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.patchMe,
    onSuccess: (result: MeResponse) => {
      queryClient.setQueryData(queryKeys.me, result);
      // The season toggle changes what is scheduled from now on.
      queryClient.invalidateQueries({ queryKey: queryKeys.today });
      queryClient.invalidateQueries({ queryKey: ["week"] });
      queryClient.invalidateQueries({ queryKey: ["month"] });
    },
  });
};

export const useChangePin = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ current, next }: { current: string; next: string }) =>
      api.changePin(current, next),
    onSuccess: (result: MeResponse) => queryClient.setQueryData(queryKeys.me, result),
  });
};

/** Anything that changes the shape of the board: habits and buckets. */
function useBoardMutation<TVariables, TResult>(
  mutationFn: (variables: TVariables) => Promise<TResult>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["habits"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.buckets });
      queryClient.invalidateQueries({ queryKey: queryKeys.today });
    },
  });
}

export const useCreateHabit = () => useBoardMutation<api.HabitBody, HabitOut>(api.createHabit);

export const useUpdateHabit = () =>
  useBoardMutation<{ id: number; patch: api.HabitPatch }, HabitOut>(({ id, patch }) =>
    api.updateHabit(id, patch),
  );

export const useSetSchedule = () =>
  useBoardMutation<{ id: number; weekdays: number[] }, HabitOut>(({ id, weekdays }) =>
    api.setSchedule(id, weekdays),
  );

export const useArchiveHabit = () => useBoardMutation<number, HabitOut>(api.archiveHabit);

export const useReorderHabits = () =>
  useBoardMutation<{ habit_id: number; sort_order: number }[], HabitOut[]>(
    api.reorderHabits,
  );

export const useCreateBucket = () =>
  useBoardMutation<api.BucketBody, BucketOut>(api.createBucket);

export const useUpdateBucket = () =>
  useBoardMutation<{ id: number; patch: Partial<api.BucketBody> }, BucketOut>(
    ({ id, patch }) => api.updateBucket(id, patch),
  );

export type { MonthView, WeekView };
