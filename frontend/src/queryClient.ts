/**
 * The query client, and the cache that survives being closed.
 *
 * Offline behaviour this phase is **read-only**: the app shell is precached by
 * the service worker and the last-known board comes from this persisted cache,
 * so opening on the train shows you your day. Ticking still needs a connection
 * — there is deliberately no mutation queue, because replaying ticks against a
 * day-boundary edit window is a genuine sync problem, not a small one.
 */

import { createSyncStoragePersister } from "@tanstack/query-sync-storage-persister";
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // The board changes when you tick it, not on its own.
      staleTime: 30_000,
      gcTime: 1000 * 60 * 60 * 24 * 3,
      retry: 1,
      refetchOnWindowFocus: true,
    },
    mutations: {
      // A failed tick rolls back and tells you why; silently retrying a
      // mutation the person can see the result of would be confusing.
      retry: 0,
    },
  },
});

export const persister = createSyncStoragePersister({
  storage: typeof window === "undefined" ? undefined : window.localStorage,
  key: "habbi.query-cache",
});
