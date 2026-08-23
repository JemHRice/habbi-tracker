/**
 * Settings: who you are, your timezone, the season toggle, and your PIN.
 *
 * `reminders_enabled` is shown but never editable. The field exists so
 * notifications aren't a schema rewrite later; the product decision is that
 * this app does not nudge, so there is nothing to switch on.
 */

import { useState } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import { useChangePin, useMe, usePatchMe } from "../api/queries";
import { useAuth } from "../auth/AuthContext";
import { Notice } from "../components/Notice";
import styles from "./Settings.module.css";

/** A short list of zones, plus whatever the user already has. */
const COMMON_ZONES = [
  "Australia/Sydney",
  "Australia/Melbourne",
  "Australia/Brisbane",
  "Australia/Perth",
  "Australia/Adelaide",
  "Pacific/Auckland",
  "Europe/London",
  "America/New_York",
  "America/Los_Angeles",
];

export function Settings() {
  const { data, isPending } = useMe();
  const patchMe = usePatchMe();
  const changePin = useChangePin();
  const { signOut, forgetDevice } = useAuth();

  const [name, setName] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [currentPin, setCurrentPin] = useState("");
  const [newPin, setNewPin] = useState("");
  const [pinError, setPinError] = useState<string | null>(null);

  if (isPending || !data) {
    return <p className={styles.quiet}>Loading…</p>;
  }

  const displayName = name ?? data.display_name;

  const saveName = () => {
    const trimmed = displayName.trim();
    if (!trimmed || trimmed === data.display_name) return;
    patchMe.mutate(
      { display_name: trimmed },
      {
        onSuccess: () => setNotice("Name saved."),
        onError: () => setNotice("Couldn't save that just now."),
      },
    );
  };

  const submitPin = (event: React.FormEvent) => {
    event.preventDefault();
    setPinError(null);
    changePin.mutate(
      { current: currentPin, next: newPin },
      {
        onSuccess: () => {
          setCurrentPin("");
          setNewPin("");
          setNotice("PIN changed.");
        },
        onError: (error) =>
          setPinError(error instanceof ApiError ? error.message : "That didn't work."),
      },
    );
  };

  const zones = COMMON_ZONES.includes(data.timezone)
    ? COMMON_ZONES
    : [data.timezone, ...COMMON_ZONES];

  return (
    <div>
      <h1 className={styles.heading}>Settings</h1>

      {data.must_change_pin ? (
        <div className={styles.banner}>
          <strong>Your PIN was set up for you.</strong> Choose your own below when
          you have a moment.
        </div>
      ) : null}

      <section className={styles.section}>
        <h2 className={styles.sectionHeading}>You</h2>

        <label className={styles.field}>
          <span className={styles.label}>Display name</span>
          <input
            className={styles.input}
            value={displayName}
            onChange={(event) => setName(event.target.value)}
            onBlur={saveName}
            maxLength={80}
          />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>Timezone</span>
          <select
            className={styles.input}
            value={data.timezone}
            onChange={(event) =>
              patchMe.mutate(
                { timezone: event.target.value },
                { onError: () => setNotice("Couldn't change your timezone.") },
              )
            }
          >
            {zones.map((zone) => (
              <option key={zone} value={zone}>
                {zone}
              </option>
            ))}
          </select>
          <span className={styles.hint}>
            Sets your day boundary — when today becomes yesterday.
          </span>
        </label>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionHeading}>Your board</h2>

        <div className={styles.toggleRow}>
          <span>
            <span className={styles.label}>Season</span>
            <span className={styles.hint}>
              When off, season habits simply aren't scheduled. Nothing is counted
              against you.
            </span>
          </span>
          <button
            type="button"
            role="switch"
            aria-checked={data.season_active}
            className={[styles.switch, data.season_active ? styles.switchOn : ""]
              .filter(Boolean)
              .join(" ")}
            onClick={() =>
              patchMe.mutate(
                { season_active: !data.season_active },
                { onError: () => setNotice("Couldn't change that just now.") },
              )
            }
          >
            <span className={styles.knob} />
            <span className="sr-only">Season active</span>
          </button>
        </div>

        <div className={styles.toggleRow}>
          <span>
            <span className={styles.label}>Reminders</span>
            <span className={styles.hint}>
              Deliberately not built. This app doesn't nudge.
            </span>
          </span>
          <span className={styles.disabledPill}>Off</span>
        </div>

        <Link to="/settings/habits" className={styles.linkButton}>
          Manage habits and buckets ›
        </Link>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionHeading}>PIN</h2>
        <form className={styles.pinForm} onSubmit={submitPin}>
          <label className={styles.field}>
            <span className={styles.label}>Current PIN</span>
            <input
              className={styles.input}
              type="password"
              inputMode="numeric"
              autoComplete="current-password"
              value={currentPin}
              onChange={(event) => setCurrentPin(event.target.value)}
            />
          </label>
          <label className={styles.field}>
            <span className={styles.label}>New PIN</span>
            <input
              className={styles.input}
              type="password"
              inputMode="numeric"
              autoComplete="new-password"
              value={newPin}
              onChange={(event) => setNewPin(event.target.value)}
            />
            <span className={styles.hint}>Six digits.</span>
          </label>
          {pinError ? <p className={styles.error}>{pinError}</p> : null}
          <button
            type="submit"
            className={styles.primary}
            disabled={changePin.isPending || !currentPin || !newPin}
          >
            Change PIN
          </button>
        </form>
      </section>

      <section className={styles.section}>
        <button type="button" className={styles.secondary} onClick={() => void signOut()}>
          Sign out
        </button>
        <button type="button" className={styles.textButton} onClick={forgetDevice}>
          Forget this device
        </button>
        <p className={styles.hint}>
          Forgetting makes this device ask "who are you?" again next time.
        </p>
      </section>

      <Notice message={notice} onDismiss={() => setNotice(null)} />
    </div>
  );
}
