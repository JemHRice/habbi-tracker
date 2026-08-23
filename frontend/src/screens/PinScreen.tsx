/**
 * The daily PIN screen.
 *
 * The device already knows whose it is, so this is the whole of signing in: six
 * digits, once each morning. An on-screen keypad rather than a text field —
 * bigger targets, no keyboard sliding over the layout, and it suits a thumb.
 */

import { useState } from "react";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Habbi } from "../components/Habbi";
import styles from "./Auth.module.css";

const PIN_LENGTH = 6;
const KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "del"];

export function PinScreen() {
  const { signIn, forgetDevice } = useAuth();
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (value: string) => {
    setBusy(true);
    setError(null);
    try {
      await signIn(value);
    } catch (caught) {
      setPin("");
      if (caught instanceof ApiError) {
        setError(
          caught.isOffline
            ? "We'll need signal to sign you in."
            : caught.message,
        );
      } else {
        setError("That didn't work. Try again.");
      }
    } finally {
      setBusy(false);
    }
  };

  const press = (key: string) => {
    if (busy) return;
    setError(null);

    if (key === "del") {
      setPin((current) => current.slice(0, -1));
      return;
    }

    setPin((current) => {
      if (current.length >= PIN_LENGTH) return current;
      const next = current + key;
      if (next.length === PIN_LENGTH) void submit(next);
      return next;
    });
  };

  return (
    <div className={styles.screen}>
      <Habbi pose="encourage" size={128} />
      <h1 className={styles.title}>Good morning</h1>
      <p className={styles.subtitle}>Your PIN, and you're in for the day.</p>

      <div className={styles.pips} role="status" aria-label={`${pin.length} of ${PIN_LENGTH} digits entered`}>
        {Array.from({ length: PIN_LENGTH }, (_, index) => (
          <span
            key={index}
            className={[styles.pip, index < pin.length ? styles.pipFilled : ""]
              .filter(Boolean)
              .join(" ")}
          />
        ))}
      </div>

      <p className={styles.error} role="alert">
        {error ?? " "}
      </p>

      <div className={styles.keypad}>
        {KEYS.map((key, index) =>
          key === "" ? (
            <span key={index} />
          ) : (
            <button
              key={index}
              type="button"
              className={styles.key}
              onClick={() => press(key)}
              disabled={busy}
              aria-label={key === "del" ? "Delete" : key}
            >
              {key === "del" ? "⌫" : key}
            </button>
          ),
        )}
      </div>

      <button type="button" className={styles.textButton} onClick={forgetDevice}>
        Not you?
      </button>
    </div>
  );
}
