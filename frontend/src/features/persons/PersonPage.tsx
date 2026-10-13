import { Calendar, CalendarPlus, Clock, FileText, ScanLine, User } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";
import { useMediaQuery } from "@/app/chrome";
import { EmptyState } from "@/design-system/components/EmptyState";
import { Notice } from "@/design-system/components/Notice";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Row, RowList } from "@/design-system/components/Row";
import { Sheet } from "@/design-system/components/Sheet";
import { BodyMap, type Marker } from "@/features/bodymap/BodyMap";
import { ViewToggle } from "@/features/bodymap/ViewToggle";
import { type MapPoint, type View, type Zone } from "@/features/bodymap/zones";
import { LesionList } from "@/features/lesions/LesionList";
import { NewLesionForm } from "@/features/lesions/NewLesionForm";
import { lesionTitle } from "@/features/lesions/lesionName";
import { shortDate } from "@/lib/dates";
import { useAppointments } from "@/lib/appointments";
import { formatBytes, useUsage } from "@/lib/data";
import { useCreateLesion, useLesions } from "@/lib/lesions";
import { useCalendarFeed } from "@/lib/notifications";
import { usePerson } from "@/lib/persons";
import { useReports } from "@/lib/reports";
import { usePersonSessions } from "@/lib/sessions";
import { personRail } from "./personRail";
import styles from "./persons.module.css";

/** A person: the body map with the marks on it, the marks as rows, and the tools used once a season. */
export function PersonPage() {
  const { personId = "" } = useParams();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const desktop = useMediaQuery("(min-width: 900px)");
  const person = usePerson(personId);
  const lesions = useLesions(personId);
  const create = useCreateLesion(personId);
  const [view, setView] = useState<View>("front");
  const [zone, setZone] = useState<Zone | null>(null);
  const [placing, setPlacing] = useState(false);
  const [point, setPoint] = useState<MapPoint | null>(null);
  const canEdit = person.data?.my_role === "owner" || person.data?.my_role === "manager";
  const dueCount = (lesions.data ?? []).filter((lesion) => lesion.due).length;

  const markers: Marker[] = (lesions.data ?? [])
    .filter((lesion) => lesion.location.view === view)
    .map((lesion) => ({
      id: lesion.id,
      x: lesion.location.x,
      y: lesion.location.y,
      label: lesionTitle(lesion, t),
      due: lesion.due,
      selected: false,
    }));

  function changeView(next: View) {
    setView(next);
    setZone(null);
    setPoint(null);
  }

  function cancelPlacing() {
    setPlacing(false);
    setPoint(null);
  }

  const zoneLabel = (code: string, name: string) => t(`zones.${code}`, { defaultValue: name });
  const instruction = !placing
    ? undefined
    : zone
      ? t("lesions.placingSpot", { zone: zoneLabel(zone.code, zone.name) })
      : t("lesions.placingHint");

  return (
    <div className={[styles.page, "page-wide"].join(" ")}>
      <PageHeader
        back={{ to: "/", label: t("shell.persons") }}
        title={person.data?.display_name ?? "…"}
        meta={[
          person.data ? t(`persons.role.${person.data.my_role}`) : null,
          lesions.data ? t("lesions.marksCount", { count: lesions.data.length }) : null,
          dueCount > 0 ? t("reminders.dueCount", { count: dueCount }) : null,
        ]}
        primary={
          canEdit && !placing ? { label: t("lesions.add"), onClick: () => setPlacing(true) } : undefined
        }
        secondary={placing ? { label: t("common.cancel"), onClick: cancelPlacing } : undefined}
        instruction={instruction}
        rail={personRail(t, personId, person.data?.display_name)}
      />
      {person.error && <Notice kind="error">{person.error.message}</Notice>}

      <div className={styles.layout}>
        <div className={styles.mapPane}>
          <ViewToggle view={view} onChange={changeView} />
          <BodyMap
            view={view}
            markers={markers}
            selectedZone={placing ? (point?.zone ?? zone?.code) : zone?.code}
            onSelectZone={setZone}
            onPlace={(next) => placing && setPoint(next)}
            placing={placing}
            onSelectMarker={(id) => void navigate(`/lesions/${id}`)}
          />
          {(lesions.data?.length ?? 0) > 0 && (
            <p className={["text-secondary", styles.legend].join(" ")} aria-hidden="true">
              <span className={styles.dot} /> {t("bodymap.tracked")}
              <span className={[styles.dot, styles.dotDue].join(" ")} /> {t("bodymap.due")}
            </p>
          )}
        </div>

        <div className={styles.detailPane}>
          {lesions.error && <Notice kind="error">{lesions.error.message}</Notice>}
          {lesions.data && lesions.data.length === 0 && (
            <EmptyState>{canEdit ? t("lesions.emptyTextEdit") : t("lesions.emptyTextView")}</EmptyState>
          )}
          {lesions.data && lesions.data.length > 0 && (
            <section aria-label={t("lesions.title")}>
              {desktop && <h2 className={styles.paneTitle}>{t("lesions.title")}</h2>}
              <LesionList lesions={lesions.data} />
            </section>
          )}
          {!desktop && person.data && (
            <Tools personId={personId} canEdit={canEdit} locale={i18n.resolvedLanguage ?? "en"} />
          )}
        </div>
      </div>

      <Sheet open={placing && point !== null} title={t("lesions.newTitle")} onClose={() => setPoint(null)}>
        {point && (
          <NewLesionForm
            point={point}
            view={view}
            pending={create.isPending}
            error={create.error?.message}
            onCancel={() => setPoint(null)}
            onSubmit={(body) =>
              create.mutate(body, {
                onSuccess: (lesion) => {
                  cancelPlacing();
                  void navigate(`/lesions/${lesion.id}`);
                },
              })
            }
          />
        )}
      </Sheet>
    </div>
  );
}

/** The five tools as rows with a one-line status each; on the desktop they live in the rail. */
function Tools({ personId, canEdit, locale }: { personId: string; canEdit: boolean; locale: string }) {
  const { t } = useTranslation();
  const appointments = useAppointments(personId);
  const sessions = usePersonSessions(personId);
  const reports = useReports(personId);
  const feed = useCalendarFeed(personId);
  const usage = useUsage(personId);
  const person = usePerson(personId);
  const today = new Date().toISOString().slice(0, 10);
  const ahead = (appointments.data ?? []).filter((item) => item.date >= today)[0];
  const open = (sessions.data ?? []).find((session) => session.status === "open");
  const last = (sessions.data ?? [])[0];
  const base = `/persons/${personId}`;

  const appointmentStatus = ahead
    ? `${shortDate(locale, ahead.date)} · ${t("appointments.progress", {
        done: ahead.checklist.filter((entry) => entry.state === "photographed").length,
        total: ahead.checklist.length,
      })}`
    : t("appointments.nonePlanned");
  const sessionStatus = open
    ? `${t("sessions.open")} · ${t("sessions.regionsCount", { captured: open.captured, total: open.captured + open.skipped + open.pending })}`
    : last
      ? t("sessions.last", { date: shortDate(locale, last.started_at) })
      : t("sessions.none");
  const reportStatus = reports.data?.length
    ? t("reports.made", { count: reports.data.length })
    : t("reports.none");
  const calendarStatus = feed.data?.exists
    ? t("calendar.linkedSince", {
        date: feed.data.created_at ? shortDate(locale, feed.data.created_at) : "",
      })
    : t("calendar.notLinked");
  const profileStatus = [
    person.data?.experimental_analysis ? t("persons.analysisOn") : t("persons.analysisOff"),
    usage.data
      ? t("data.usage", { count: usage.data.images, size: formatBytes(usage.data.bytes, locale) })
      : null,
  ]
    .filter(Boolean)
    .join(" · ");

  const rows = [
    {
      to: `${base}/appointments`,
      icon: <Calendar />,
      title: t("appointments.sectionTitle"),
      meta: appointmentStatus,
      live: Boolean(ahead),
      show: canEdit || (appointments.data?.length ?? 0) > 0,
    },
    {
      to: `${base}/sessions`,
      icon: <ScanLine />,
      title: t("sessions.title"),
      meta: sessionStatus,
      live: Boolean(open),
      show: canEdit || (sessions.data?.length ?? 0) > 0,
    },
    {
      to: `${base}/reports`,
      icon: <FileText />,
      title: t("reports.title"),
      meta: reportStatus,
      live: false,
      show: true,
    },
    {
      to: `${base}/calendar`,
      icon: <CalendarPlus />,
      title: t("calendar.title"),
      meta: calendarStatus,
      live: false,
      show: true,
    },
    {
      to: `${base}/profile`,
      icon: <User />,
      title: t("persons.profile"),
      meta: profileStatus,
      live: false,
      show: person.data?.my_role === "owner",
    },
  ]
    .filter((row) => row.show)
    .sort((a, b) => Number(b.live) - Number(a.live));

  return (
    <RowList className={styles.tools} label={t("persons.profileTitle")}>
      {rows.map((row) => (
        <Row
          key={row.to}
          to={row.to}
          leading={row.live ? <Clock /> : row.icon}
          title={row.title}
          meta={<span className={row.live ? styles.live : undefined}>{row.meta}</span>}
          chevron
        />
      ))}
    </RowList>
  );
}
