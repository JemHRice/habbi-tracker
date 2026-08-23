/**
 * What the device remembers.
 *
 * Two separate things, with different lifetimes:
 *
 * - **Which user this device belongs to.** Set once, on first run, and kept
 *   until storage is cleared. This is what means you never see a
 *   "who are you?" screen twice.
 * - **The session.** A token and its expiry, good until the next local
 *   midnight. Expired sessions are dropped on read, so a stale token is never
 *   handed to the API.
 */

const BOUND_USER_KEY = "habbi.boundUserId";
const SESSION_KEY = "habbi.session";

export interface StoredSession {
  token: string;
  expiresAt: string;
  userId: number;
}

function safeGet(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    // Private mode, or storage disabled. The app still works, it just forgets.
    return null;
  }
}

function safeSet(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* nothing we can do, and nothing worth interrupting the person for */
  }
}

function safeRemove(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    /* as above */
  }
}

export function readBoundUserId(): number | null {
  const raw = safeGet(BOUND_USER_KEY);
  if (raw === null) return null;
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) ? parsed : null;
}

export function writeBoundUserId(userId: number): void {
  safeSet(BOUND_USER_KEY, String(userId));
}

export function clearBoundUserId(): void {
  safeRemove(BOUND_USER_KEY);
}

/** Return the stored session, or null if it is missing or already expired. */
export function readSession(now: Date = new Date()): StoredSession | null {
  const raw = safeGet(SESSION_KEY);
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as StoredSession;
    if (!parsed.token || !parsed.expiresAt) return null;
    if (new Date(parsed.expiresAt).getTime() <= now.getTime()) {
      safeRemove(SESSION_KEY);
      return null;
    }
    return parsed;
  } catch {
    safeRemove(SESSION_KEY);
    return null;
  }
}

export function writeSession(session: StoredSession): void {
  safeSet(SESSION_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  safeRemove(SESSION_KEY);
}
