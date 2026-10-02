import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import styles from "./auth.module.css";

/** The sign-in pages: the brand on its dark paper, the form centred in the page, the tagline below. */
export function AuthLayout({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  return (
    <div className={styles.page}>
      <header className={styles.brand}>
        <img src="/brand/wordmark-dark.svg" alt={t("app.name")} width={192} height={90} />
      </header>
      <main className={styles.main}>{children}</main>
      <footer className={styles.tagline}>{t("app.tagline")}</footer>
    </div>
  );
}
