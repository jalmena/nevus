import { useTranslation } from "react-i18next";
import { useInstance } from "@/lib/auth/session";
import { SettingsHeader } from "./SettingsHeader";
import styles from "./settings.module.css";

/** What this is for, and which version it is. */
export function AboutSection({ admin }: { admin: boolean }) {
  const { t } = useTranslation();
  const instance = useInstance();
  return (
    <div className={styles.page}>
      <SettingsHeader
        admin={admin}
        title={t("settings.about")}
        meta={[t("settings.version", { version: instance.data?.version ?? "" })]}
      />
      <p className="text-secondary">{t("app.intendedUse")}</p>
    </div>
  );
}
