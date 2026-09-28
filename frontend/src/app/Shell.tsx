import { NavLink, Outlet } from "react-router";
import { useTranslation } from "react-i18next";
import styles from "./Shell.module.css";

/** Brand block on the dark paper, content below, a small navigation bar. */
export function Shell() {
  const { t } = useTranslation();
  return (
    <div className={styles.page}>
      <header className={styles.brand}>
        <NavLink to="/" aria-label={t("app.name")}>
          <img src="/brand/wordmark-dark.svg" alt="" width={160} height={75} />
        </NavLink>
        <nav className={styles.nav} aria-label={t("shell.navigation")}>
          <NavLink to="/" end className={({ isActive }) => (isActive ? styles.active : undefined)}>
            {t("shell.persons")}
          </NavLink>
          <NavLink to="/settings" className={({ isActive }) => (isActive ? styles.active : undefined)}>
            {t("settings.title")}
          </NavLink>
        </nav>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
