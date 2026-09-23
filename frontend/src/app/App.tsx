import { useTranslation } from "react-i18next";
import { supportedLanguages, type Language } from "@/lib/i18n";
import styles from "./App.module.css";

export function App() {
  const { t, i18n } = useTranslation();
  return (
    <div className={styles.page}>
      <header className={styles.brand}>
        <img src="/brand/wordmark-dark.svg" alt={t("app.name")} width={288} height={135} />
        <p className={styles.tagline}>{t("app.tagline")}</p>
      </header>
      <main className={styles.main}>
        <p>{t("shell.comingSoon")}</p>
        <p className="text-secondary">{t("app.intendedUse")}</p>
        <label className={styles.language}>
          <span>{t("shell.language")}</span>
          <select
            value={i18n.resolvedLanguage ?? "en"}
            onChange={(event) => void i18n.changeLanguage(event.target.value as Language)}
          >
            {supportedLanguages.map((code) => (
              <option key={code} value={code}>
                {t(`languages.${code}`)}
              </option>
            ))}
          </select>
        </label>
      </main>
    </div>
  );
}
