import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Card } from "@/design-system/components/Card";
import { Notice } from "@/design-system/components/Notice";
import { useInstance, useLogout, useSession, useUpdateMe } from "@/lib/auth/session";
import { supportedLanguages } from "@/lib/i18n";
import styles from "./settings.module.css";

const THEMES = ["system", "light", "dark"] as const;

export function SettingsPage() {
  const { t } = useTranslation();
  const session = useSession();
  const instance = useInstance();
  const update = useUpdateMe();
  const logout = useLogout();
  const user = session.data?.user;
  if (!user) return null;
  return (
    <div className={styles.page}>
      <h1>{t("settings.title")}</h1>
      <Card className={styles.group}>
        <label className={styles.row}>
          <span>{t("shell.language")}</span>
          <select
            value={user.language}
            onChange={(e) => update.mutate({ language: e.target.value as "en" | "es" })}
          >
            {supportedLanguages.map((code) => (
              <option key={code} value={code}>
                {t(`languages.${code}`)}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.row}>
          <span>{t("settings.theme")}</span>
          <select
            value={user.theme}
            onChange={(e) => update.mutate({ theme: e.target.value as (typeof THEMES)[number] })}
          >
            {THEMES.map((theme) => (
              <option key={theme} value={theme}>
                {t(`settings.themes.${theme}`)}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.row}>
          <span>{t("settings.showUncertainty")}</span>
          <input
            type="checkbox"
            checked={user.show_uncertainty}
            onChange={(e) => update.mutate({ show_uncertainty: e.target.checked })}
          />
        </label>
        {update.error && <Notice kind="error">{update.error.message}</Notice>}
      </Card>
      <Card className={styles.group}>
        <p>
          <strong>{user.username}</strong> · {t(`settings.roles.${user.role}`)}
        </p>
        <Button variant="secondary" onClick={() => logout.mutate()}>
          {t("settings.signOut")}
        </Button>
      </Card>
      <Card className={styles.group}>
        <p className="text-secondary">{t("app.intendedUse")}</p>
        <p className="text-secondary numeric">neVus {instance.data?.version}</p>
      </Card>
    </div>
  );
}
