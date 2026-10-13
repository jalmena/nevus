import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Help } from "@/design-system/components/Help";
import { Notice } from "@/design-system/components/Notice";
import { Switch } from "@/design-system/components/Switch";
import { TextField } from "@/design-system/components/TextField";
import { useSession, useUpdateMe } from "@/lib/auth/session";
import { SettingsHeader } from "./SettingsHeader";
import styles from "./settings.module.css";

/** The daily email: the address, saved as soon as it is left, and whether to send it. */
export function ReminderSettings({ admin }: { admin: boolean }) {
  const { t } = useTranslation();
  const user = useSession().data?.user;
  const update = useUpdateMe();
  const [address, setAddress] = useState(user?.email ?? "");
  if (!user) return null;

  function saveAddress() {
    const next = address.trim() || null;
    if (next !== (user?.email ?? null)) update.mutate({ email: next });
  }

  return (
    <div className={styles.page}>
      <SettingsHeader
        admin={admin}
        title={t("reminders.settingsTitle")}
        meta={[user.email_reminders ? t("settings.status.emailOn") : t("settings.status.emailOff")]}
      >
        <p className={["text-secondary", styles.intro].join(" ")}>
          {t("reminders.settingsShort")}
          <Help title={t("reminders.settingsTitle")} as="text">
            <p>{t("reminders.settingsIntro")}</p>
          </Help>
        </p>
      </SettingsHeader>
      <form
        className={styles.form}
        onSubmit={(event) => {
          event.preventDefault();
          saveAddress();
        }}
      >
        <TextField
          label={t("reminders.email")}
          type="email"
          autoComplete="email"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          onBlur={saveAddress}
        />
      </form>
      <Switch
        label={t("reminders.emailReminders")}
        hint={!user.email ? t("reminders.needEmail") : undefined}
        checked={user.email_reminders}
        disabled={!user.email}
        onChange={(checked) => update.mutate({ email_reminders: checked })}
      />
      {update.isSuccess && (
        <p className="text-secondary" role="status">
          {t("common.saved")}
        </p>
      )}
      {update.error && <Notice kind="error">{update.error.message}</Notice>}
    </div>
  );
}
