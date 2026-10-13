import { Columns2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { EmptyState } from "@/design-system/components/EmptyState";
import { Notice } from "@/design-system/components/Notice";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Row, RowList } from "@/design-system/components/Row";
import { personRail } from "@/features/persons/personRail";
import { shortDate } from "@/lib/dates";
import type { PersonOut } from "@/lib/persons";
import { usePersonSessions, useStartSession } from "@/lib/sessions";
import styles from "./sessions.module.css";

/** The person's full-body sessions as a page: the ones made, comparing the last two, starting a new one. */
export function SessionsSection({ person, canEdit }: { person: PersonOut; canEdit: boolean }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const sessions = usePersonSessions(person.id);
  const start = useStartSession(person.id);
  const list = sessions.data ?? [];
  const withPhotos = list.filter((session) => session.captured > 0);
  const [latest, previous] = withPhotos;
  return (
    <div className={styles.page}>
      <PageHeader
        help={{
          title: t("sessions.title"),
          content: (
            <>
              <p>{t("sessions.hint")}</p>
              <p>{t("sessions.intro")}</p>
            </>
          ),
        }}
        back={{ to: `/persons/${person.id}`, label: person.display_name }}
        title={t("sessions.title")}
        meta={[
          sessions.data
            ? list.length > 0
              ? t("sessions.count", { count: list.length })
              : t("sessions.none")
            : null,
        ]}
        rail={personRail(t, person.id, person.display_name)}
        actions={
          latest && previous
            ? [
                {
                  key: "compare",
                  label: t("sessions.compareLatest"),
                  icon: <Columns2 />,
                  to: `/sessions/${latest.id}/compare/${previous.id}`,
                },
              ]
            : []
        }
        primary={
          canEdit
            ? {
                label: t("sessions.start"),
                pending: start.isPending,
                onClick: () =>
                  start.mutate(null, { onSuccess: (session) => void navigate(`/sessions/${session.id}`) }),
              }
            : undefined
        }
      ></PageHeader>
      {(sessions.error ?? start.error) && (
        <Notice kind="error">{(sessions.error ?? start.error)?.message}</Notice>
      )}
      {sessions.data && list.length === 0 && <EmptyState>{t("sessions.empty")}</EmptyState>}
      {list.length > 0 && (
        <RowList>
          {list.map((session) => (
            <Row
              key={session.id}
              to={`/sessions/${session.id}`}
              title={t("sessions.titleFor", { date: shortDate(i18n.resolvedLanguage, session.started_at) })}
              meta={[
                session.status === "open" ? t("sessions.open") : t("sessions.finished"),
                t("sessions.regionsCount", {
                  captured: session.captured,
                  total: session.captured + session.skipped + session.pending,
                }),
                session.skipped > 0 ? t("sessions.skippedCount", { count: session.skipped }) : null,
                t("sessions.marksCount", { count: session.marks }),
              ]
                .filter(Boolean)
                .join(" · ")}
            />
          ))}
        </RowList>
      )}
    </div>
  );
}
