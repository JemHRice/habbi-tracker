/**
 * Routing, and the gate in front of it.
 *
 * Three states, checked in order: the device doesn't know who it is (pick), it
 * knows but has no live session (PIN), or it's signed in (the app). Any 401
 * collapses the third state back into the second, so the gate is the only place
 * that decides what you see.
 */

import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { DayDetail } from "./screens/DayDetail";
import { Habits } from "./screens/Habits";
import { PinScreen } from "./screens/PinScreen";
import { Settings } from "./screens/Settings";
import { Today } from "./screens/Today";
import { Tracking } from "./screens/Tracking";
import { WhoAreYou } from "./screens/WhoAreYou";

export function App() {
  const { boundUserId, isSignedIn } = useAuth();

  if (boundUserId === null) return <WhoAreYou />;
  if (!isSignedIn) return <PinScreen />;

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Today />} />
        <Route path="/tracking" element={<Tracking />} />
        <Route path="/days/:date" element={<DayDetail />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/settings/habits" element={<Habits />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
