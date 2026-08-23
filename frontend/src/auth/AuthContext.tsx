/**
 * Who this device belongs to, and whether there is a live session.
 *
 * The flow the backend expects: bind the device once, then enter a PIN each
 * morning. A session dies at the next local midnight, and any 401 drops
 * straight back to the PIN screen.
 */

import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { onUnauthorized, setTokenProvider } from "../api/client";
import * as api from "../api/endpoints";
import {
  clearBoundUserId,
  clearSession,
  readBoundUserId,
  readSession,
  writeBoundUserId,
  writeSession,
  type StoredSession,
} from "./storage";

interface AuthValue {
  /** The user this device is bound to, or null before first run. */
  boundUserId: number | null;
  session: StoredSession | null;
  isSignedIn: boolean;
  mustChangePin: boolean;
  bindDevice: (userId: number) => void;
  forgetDevice: () => void;
  signIn: (pin: string) => Promise<void>;
  signOut: () => Promise<void>;
  clearMustChangePin: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [boundUserId, setBoundUserId] = useState<number | null>(() => readBoundUserId());
  const [session, setSession] = useState<StoredSession | null>(() => readSession());
  const [mustChangePin, setMustChangePin] = useState(false);

  // The API client reads the token through a getter so it always sees the
  // current one without the module importing React state.
  useEffect(() => {
    setTokenProvider(() => session?.token ?? null);
  }, [session]);

  const endSession = useCallback(() => {
    clearSession();
    setSession(null);
    setMustChangePin(false);
    queryClient.clear();
  }, [queryClient]);

  // A 401 from anywhere means the day boundary passed or the token was
  // revoked. There is exactly one correct response, so it lives here.
  useEffect(() => onUnauthorized(endSession), [endSession]);

  // A session is only good until midnight, and the app may sit open across it.
  useEffect(() => {
    if (!session) return;
    const remaining = new Date(session.expiresAt).getTime() - Date.now();
    if (remaining <= 0) {
      endSession();
      return;
    }
    const timer = window.setTimeout(endSession, remaining);
    return () => window.clearTimeout(timer);
  }, [session, endSession]);

  const bindDevice = useCallback((userId: number) => {
    writeBoundUserId(userId);
    setBoundUserId(userId);
  }, []);

  const forgetDevice = useCallback(() => {
    clearBoundUserId();
    clearSession();
    setBoundUserId(null);
    setSession(null);
    queryClient.clear();
  }, [queryClient]);

  const signIn = useCallback(
    async (pin: string) => {
      if (boundUserId === null) {
        throw new Error("This device is not bound to a user yet.");
      }
      const result = await api.login(boundUserId, pin);
      const next: StoredSession = {
        token: result.token,
        expiresAt: result.expires_at,
        userId: boundUserId,
      };
      writeSession(next);
      setSession(next);
      setMustChangePin(result.must_change_pin);
    },
    [boundUserId],
  );

  const signOut = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // Already gone, or offline. Either way the device is signing out.
    }
    endSession();
  }, [endSession]);

  const value = useMemo<AuthValue>(
    () => ({
      boundUserId,
      session,
      isSignedIn: session !== null,
      mustChangePin,
      bindDevice,
      forgetDevice,
      signIn,
      signOut,
      clearMustChangePin: () => setMustChangePin(false),
    }),
    [boundUserId, session, mustChangePin, bindDevice, forgetDevice, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside an AuthProvider");
  return value;
}
