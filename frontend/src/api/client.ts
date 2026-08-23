/**
 * The single place the app talks to the network.
 *
 * Two responsibilities beyond fetching: it attaches the session token, and it
 * turns the API's error envelope into a typed `ApiError` so screens can react
 * to a *code* rather than sniffing status numbers or message strings.
 */

import type { ApiErrorCode } from "./types";

const BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

/** An error the API reported, or a network failure shaped to look like one. */
export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly status: number;

  constructor(code: ApiErrorCode, message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }

  /** True when the request never reached the server. */
  get isOffline(): boolean {
    return this.code === "OFFLINE";
  }
}

type Listener = () => void;

const unauthorizedListeners = new Set<Listener>();

/**
 * Register a callback for "the session is no longer good".
 *
 * Any 401 means the day boundary has passed or the token was revoked, and the
 * only correct response is to drop to the PIN screen. Routing that through one
 * subscription keeps every screen from having to handle it.
 */
export function onUnauthorized(listener: Listener): () => void {
  unauthorizedListeners.add(listener);
  return () => unauthorizedListeners.delete(listener);
}

let tokenProvider: () => string | null = () => null;

/** Tell the client how to find the current token. Called once, at startup. */
export function setTokenProvider(provider: () => string | null): void {
  tokenProvider = provider;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  /** Skip the Authorization header — for /users and /auth/login. */
  anonymous?: boolean;
}

async function parseError(response: Response): Promise<ApiError> {
  let code: ApiErrorCode = "VALIDATION";
  let message = response.statusText || "Something went wrong.";

  try {
    const body = (await response.json()) as {
      error?: { code?: string; message?: string };
    };
    if (body.error?.code) code = body.error.code as ApiErrorCode;
    if (body.error?.message) message = body.error.message;
  } catch {
    // A non-JSON body (a proxy error page, say). Keep the status text.
  }

  return new ApiError(code, message, response.status);
}

/** Perform a request against the API, returning parsed JSON. */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, anonymous = false } = options;

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";

  if (!anonymous) {
    const token = tokenProvider();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    // fetch only rejects when the request never completed.
    throw new ApiError("OFFLINE", "We'll need signal for that.", 0);
  }

  if (response.status === 401) {
    const error = await parseError(response);
    unauthorizedListeners.forEach((listener) => listener());
    throw error;
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const apiBaseUrl = BASE_URL;
