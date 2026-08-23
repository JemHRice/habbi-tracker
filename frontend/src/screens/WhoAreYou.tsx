/**
 * First run on a device: "who are you?".
 *
 * Shown exactly once. Picking someone binds the device to that user, and from
 * then on the app goes straight to the PIN screen. There is no sign-up here —
 * accounts are provisioned by the backend seed.
 */

import { useUsers } from "../api/queries";
import { useAuth } from "../auth/AuthContext";
import { Habbi } from "../components/Habbi";
import styles from "./Auth.module.css";

export function WhoAreYou() {
  const { data, isPending, isError, refetch } = useUsers();
  const { bindDevice } = useAuth();

  return (
    <div className={styles.screen}>
      <Habbi pose="encourage" size={150} label="Habbi waving hello" />
      <h1 className={styles.title}>Hello!</h1>
      <p className={styles.subtitle}>Which board is this device for?</p>

      {isPending ? <p className={styles.quiet}>Just a moment…</p> : null}

      {isError ? (
        <>
          <p className={styles.quiet}>We couldn't reach the app just now.</p>
          <button type="button" className={styles.secondary} onClick={() => void refetch()}>
            Try again
          </button>
        </>
      ) : null}

      {data ? (
        <ul className={styles.userList}>
          {data.map((user) => (
            <li key={user.id}>
              <button
                type="button"
                className={styles.userButton}
                onClick={() => bindDevice(user.id)}
              >
                {user.display_name}
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      <p className={styles.footnote}>
        You'll only be asked this once on this device.
      </p>
    </div>
  );
}
