import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Card } from "@/design-system/components/Card";
import { Notice } from "@/design-system/components/Notice";
import { TextField } from "@/design-system/components/TextField";
import { useSession, useUpdateMe } from "@/lib/auth/session";
import styles from "./settings.module.css";

export function ReminderSettings() {
  const { t } = useTranslation();
  const session = useSession();
  const update = useUpdateMe();
  const user = session.data?.user;
  const [address, setAddress] = useState(user?.email ?? "");
  if (!user) return null;

  function saveAddress(event: FormEvent) {
    event.preventDefault();
    update.mutate({ email: address.trim() || null });
  }

  return (
    <Card className={styles.group}>
      <h2 className={styles.subheading}>{t("reminders.settingsTitle")}</h2>
      <p className="text-secondary">{t("reminders.settingsIntro")}</p>
      <form className={styles.inline} onSubmit={saveAddress}>
        <TextField
          label={t("reminders.email")}
          type="email"
          autoComplete="email"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
        />
        <Button type="submit" variant="secondary" disabled={update.isPending}>
          {t("common.save")}
        </Button>
      </form>
      <label className={styles.row}>
        <span>{t("reminders.emailReminders")}</span>
        <input
          type="checkbox"
          checked={user.email_reminders}
          disabled={!user.email}
          onChange={(e) => update.mutate({ email_reminders: e.target.checked })}
        />
      </label>
      {!user.email && <p className="text-secondary">{t("reminders.needEmail")}</p>}
      {update.error && <Notice kind="error">{update.error.message}</Notice>}
    </Card>
  );
}
