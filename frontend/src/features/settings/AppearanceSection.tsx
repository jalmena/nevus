import { useTranslation } from "react-i18next";
import { Notice } from "@/design-system/components/Notice";
import { Row, RowList } from "@/design-system/components/Row";
import { Select } from "@/design-system/components/Select";
import { Switch } from "@/design-system/components/Switch";
import { useSession, useUpdateMe } from "@/lib/auth/session";
import { supportedLanguages, type Language } from "@/lib/i18n";
import { SettingsHeader } from "./SettingsHeader";
import styles from "./settings.module.css";

export const THEMES = ["system", "light", "dark"] as const;

/** Language, theme and whether measurements show their uncertainty; each saves as it changes. */
export function AppearanceSection({ admin }: { admin: boolean }) {
  const { t } = useTranslation();
  const user = useSession().data?.user;
  const update = useUpdateMe();
  if (!user) return null;
  return (
    <div className={styles.page}>
      <SettingsHeader admin={admin} title={t("settings.appearance")} />
      <RowList>
        <Row
          title={t("shell.language")}
          trailing={
            <Select
              label={t("shell.language")}
              labelHidden
              value={user.language}
              onChange={(e) => update.mutate({ language: e.target.value as Language })}
              options={supportedLanguages.map((code) => ({ value: code, label: t(`languages.${code}`) }))}
            />
          }
        />
        <Row
          title={t("settings.theme")}
          trailing={
            <Select
              label={t("settings.theme")}
              labelHidden
              value={user.theme}
              onChange={(e) => update.mutate({ theme: e.target.value as (typeof THEMES)[number] })}
              options={THEMES.map((theme) => ({ value: theme, label: t(`settings.themes.${theme}`) }))}
            />
          }
        />
        <li className={styles.switchRow}>
          <Switch
            label={t("settings.showUncertainty")}
            checked={user.show_uncertainty}
            onChange={(checked) => update.mutate({ show_uncertainty: checked })}
          />
        </li>
      </RowList>
      {update.isSuccess && (
        <p className="text-secondary" role="status">
          {t("common.saved")}
        </p>
      )}
      {update.error && <Notice kind="error">{update.error.message}</Notice>}
    </div>
  );
}
