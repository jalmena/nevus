import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import type { LesionOut } from "@/lib/lesions";
import { useSnooze } from "@/lib/reminders";
import styles from "./reminders.module.css";

export function SnoozeControls({ lesion, canEdit }: { lesion: LesionOut; canEdit: boolean }) {
  const { t, i18n } = useTranslation();
  const snooze = useSnooze(lesion.id);
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium" });
  if (lesion.snoozed_until) {
    return (
      <div className={styles.snooze}>
        <span className="text-secondary">
          {t("reminders.snoozedUntil", { date: dateFormat.format(new Date(lesion.snoozed_until)) })}
        </span>
        {canEdit && (
          <Button variant="quiet" onClick={() => snooze.mutate(null)} disabled={snooze.isPending}>
            {t("reminders.unsnooze")}
          </Button>
        )}
      </div>
    );
  }
  if (!lesion.due || !canEdit) return null;
  return (
    <div className={styles.snooze}>
      <span>{t("reminders.notNow")}</span>
      <Button variant="secondary" onClick={() => snooze.mutate(7)} disabled={snooze.isPending}>
        {t("reminders.snoozeWeek")}
      </Button>
      <Button variant="secondary" onClick={() => snooze.mutate(30)} disabled={snooze.isPending}>
        {t("reminders.snoozeMonth")}
      </Button>
      {snooze.error && <Notice kind="error">{snooze.error.message}</Notice>}
    </div>
  );
}
