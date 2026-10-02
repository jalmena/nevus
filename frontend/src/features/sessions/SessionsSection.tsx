import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { usePersonSessions, useStartSession } from "@/lib/sessions";
import styles from "./sessions.module.css";

/** On a person's page: the full-body sessions, and starting a new one. */
export function SessionsSection({ personId, canEdit }: { personId: string; canEdit: boolean }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const sessions = usePersonSessions(personId);
  const start = useStartSession(personId);
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "long" });
  const list = sessions.data ?? [];
  const withPhotos = list.filter((session) => session.captured > 0);
  if (!canEdit && list.length === 0) return null;
  return (
    <section className={styles.section} aria-labelledby="sessions-heading">
      <h2 id="sessions-heading">{t("sessions.title")}</h2>
      <p className="text-secondary">{t("sessions.intro")}</p>
      {canEdit && (
        <div>
          <Button
            onClick={() =>
              start.mutate(null, { onSuccess: (session) => void navigate(`/sessions/${session.id}`) })
            }
            disabled={start.isPending}
          >
            {t("sessions.start")}
          </Button>
        </div>
      )}
      {start.error && <Notice kind="error">{start.error.message}</Notice>}
      {list.length > 0 && (
        <ul className={styles.list}>
          {list.map((session) => (
            <li key={session.id} className={styles.item}>
              <Link to={`/sessions/${session.id}`}>
                {t("sessions.titleFor", { date: dateFormat.format(new Date(session.started_at)) })}
              </Link>
              <span className="text-secondary">
                {session.status === "open" ? t("sessions.open") : t("sessions.finished")} ·{" "}
                {t("sessions.progress", {
                  captured: session.captured,
                  total: session.captured + session.skipped + session.pending,
                })}
                {session.skipped > 0 ? ` · ${t("sessions.skippedCount", { count: session.skipped })}` : ""} ·{" "}
                {t("sessions.marksCount", { count: session.marks })}
              </span>
            </li>
          ))}
        </ul>
      )}
      {withPhotos.length >= 2 && withPhotos[0] && withPhotos[1] && (
        <p>
          <Link to={`/sessions/${withPhotos[0].id}/compare/${withPhotos[1].id}`}>
            {t("sessions.compareLatest")}
          </Link>
        </p>
      )}
    </section>
  );
}
