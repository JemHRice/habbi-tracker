/**
 * The app shell: a scrolling page over a three-item bottom bar.
 *
 * Three destinations only — Today, Tracking, Settings — because the whole app
 * is three screens and a bottom bar is the honest shape for one-handed use.
 */

import { NavLink, Outlet } from "react-router-dom";

import styles from "./Layout.module.css";

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
}

const ITEMS: NavItem[] = [
  {
    to: "/",
    label: "Today",
    icon: (
      <path
        d="M4 12.5l6 6 10-12"
        fill="none"
        stroke="currentColor"
        strokeWidth={2.2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    ),
  },
  {
    to: "/tracking",
    label: "Tracking",
    icon: (
      <>
        <rect
          x={3.5}
          y={4.5}
          width={17}
          height={16}
          rx={3}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
        />
        <path
          d="M3.5 9.5h17M8 3v3M16 3v3"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
        />
      </>
    ),
  },
  {
    to: "/settings",
    label: "Settings",
    icon: (
      <>
        <circle cx={12} cy={12} r={3.2} fill="none" stroke="currentColor" strokeWidth={2} />
        <path
          d="M12 2.8v2.4M12 18.8v2.4M4.5 12H2.1M21.9 12h-2.4M6.4 6.4L4.7 4.7M19.3 19.3l-1.7-1.7M17.6 6.4l1.7-1.7M4.7 19.3l1.7-1.7"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
        />
      </>
    ),
  },
];

export function Layout() {
  return (
    <div className={styles.shell}>
      <main className={styles.page}>
        <Outlet />
      </main>

      <nav className={styles.bar} aria-label="Main">
        {ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              [styles.tab, isActive ? styles.tabActive : ""].filter(Boolean).join(" ")
            }
          >
            <svg viewBox="0 0 24 24" width={22} height={22} aria-hidden="true">
              {item.icon}
            </svg>
            <span className={styles.tabLabel}>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
