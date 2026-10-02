import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Card } from "@/design-system/components/Card";
import { Notice } from "@/design-system/components/Notice";
import { AdminSettings } from "@/features/admin/AdminSettings";
import { UsersAdmin } from "@/features/admin/UsersAdmin";
import { ExportForm } from "@/features/data/ExportForm";
import { ExportList } from "@/features/data/ExportList";
import { Link } from "react-router";
import { ReferenceCardSettings } from "./ReferenceCardSettings";
import { PushSettings } from "./PushSettings";
import { ReminderSettings } from "./ReminderSettings";
import { SecondFactorSettings } from "./SecondFactorSettings";
import { useInstance, useLogout, useSession, useUpdateMe } from "@/lib/auth/session";
import { supportedLanguages, type Language } from "@/lib/i18n";
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
  const admin = user.role === "admin";
  const sections = [
    { id: "account", label: t("settings.account") },
    { id: "appearance", label: t("settings.appearance") },
    { id: "reminders", label: t("reminders.settingsTitle") },
    { id: "second-factor", label: t("secondFactor.title") },
    { id: "reference-card", label: t("card.title") },
    { id: "your-data", label: t("data.title") },
    ...(admin
      ? [
          { id: "accounts", label: t("accounts.title") },
          { id: "administration", label: t("settings.administration") },
        ]
      : []),
    { id: "about", label: t("settings.about") },
  ];
  return (
    <div className={[styles.page, "page-wide"].join(" ")}>
      <h1>{t("settings.title")}</h1>
      <div className={styles.layout}>
        <nav className={styles.nav} aria-label={t("settings.sections")}>
          <ul>
            {sections.map((section) => (
              <li key={section.id}>
                <a href={`#${section.id}`}>{section.label}</a>
              </li>
            ))}
          </ul>
        </nav>
        <div className={styles.content}>
          <div id="account" className={styles.anchor}>
            <Card className={styles.group}>
              <h2 className={styles.subheading}>{t("settings.account")}</h2>
              <p>
                <strong>{user.username}</strong> · {t(`settings.roles.${user.role}`)}
              </p>
              <div>
                <Button variant="secondary" onClick={() => logout.mutate()}>
                  {t("settings.signOut")}
                </Button>
              </div>
            </Card>
          </div>
          <div id="appearance" className={styles.anchor}>
            <Card className={styles.group}>
              <h2 className={styles.subheading}>{t("settings.appearance")}</h2>
              <label className={styles.row}>
                <span>{t("shell.language")}</span>
                <select
                  value={user.language}
                  onChange={(e) => update.mutate({ language: e.target.value as Language })}
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
          </div>
          <div id="reminders" className={styles.anchor}>
            <ReminderSettings />
            <PushSettings />
          </div>
          <div id="second-factor" className={styles.anchor}>
            <SecondFactorSettings />
          </div>
          <div id="reference-card" className={styles.anchor}>
            <ReferenceCardSettings />
          </div>
          <div id="your-data" className={styles.anchor}>
            <Card className={styles.group}>
              <h2 className={styles.subheading}>{t("data.title")}</h2>
              <p className="text-secondary">{t("data.intro")}</p>
              <ExportList />
              {admin && <ExportForm personId={null} label={t("data.exportAll")} />}
              <Link to="/trash">{t("trash.open")}</Link>
            </Card>
          </div>
          {admin && (
            <div id="accounts" className={styles.anchor}>
              <UsersAdmin />
            </div>
          )}
          {admin && (
            <div id="administration" className={styles.anchor}>
              <AdminSettings />
            </div>
          )}
          <div id="about" className={styles.anchor}>
            <Card className={styles.group}>
              <h2 className={styles.subheading}>{t("settings.about")}</h2>
              <p className="text-secondary">{t("app.intendedUse")}</p>
              <p className="text-secondary numeric">neVus {instance.data?.version}</p>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
