import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";
import { Button } from "@/design-system/components/Button";
import { Disclosure } from "@/design-system/components/Disclosure";
import { EmptyState } from "@/design-system/components/EmptyState";
import { Notice } from "@/design-system/components/Notice";
import { BodyMap, type Marker } from "@/features/bodymap/BodyMap";
import { ViewToggle } from "@/features/bodymap/ViewToggle";
import { type MapPoint, type View, type Zone } from "@/features/bodymap/zones";
import { LesionList } from "@/features/lesions/LesionList";
import { NewLesionForm } from "@/features/lesions/NewLesionForm";
import { lesionTitle } from "@/features/lesions/lesionName";
import { useCreateLesion, useLesions } from "@/lib/lesions";
import { ExportForm } from "@/features/data/ExportForm";
import { PurgePerson } from "@/features/data/PurgePerson";
import { PrepareAppointment } from "@/features/appointments/PrepareAppointment";
import { Reports } from "@/features/reports/Reports";
import { SessionsSection } from "@/features/sessions/SessionsSection";
import { CalendarLink } from "./CalendarLink";
import { useAppointments } from "@/lib/appointments";
import { formatBytes, useUsage } from "@/lib/data";
import { usePersonSessions } from "@/lib/sessions";
import { usePerson, useUpdatePerson } from "@/lib/persons";
import styles from "./persons.module.css";

export function PersonPage() {
  const { personId = "" } = useParams();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const person = usePerson(personId);
  const lesions = useLesions(personId);
  const create = useCreateLesion(personId);
  const [view, setView] = useState<View>("front");
  const [zone, setZone] = useState<Zone | null>(null);
  const [placing, setPlacing] = useState(false);
  const [point, setPoint] = useState<MapPoint | null>(null);
  const canEdit = person.data?.my_role === "owner" || person.data?.my_role === "manager";
  const updatePerson = useUpdatePerson(personId);
  const usage = useUsage(personId);
  const appointments = useAppointments(personId);
  const sessions = usePersonSessions(personId);
  const today = new Date().toISOString().slice(0, 10);
  const appointmentAhead = (appointments.data ?? []).some((item) => item.date >= today);
  const sessionOpen = (sessions.data ?? []).some((session) => session.status === "open");

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

  function onPlace(next: MapPoint) {
    if (placing) setPoint(next);
  }

  function cancelPlacing() {
    setPlacing(false);
    setPoint(null);
  }

  return (
    <div className={[styles.page, "page-wide"].join(" ")}>
      <p>
        <Link to="/">{t("common.back")}</Link>
      </p>
      <header className={styles.header}>
        <h1>{person.data?.display_name ?? "…"}</h1>
        {person.data && <span className="text-secondary">{t(`persons.role.${person.data.my_role}`)}</span>}
      </header>
      {person.error && <Notice kind="error">{person.error.message}</Notice>}

      <div className={styles.layout}>
        <section className={[styles.mapSection, styles.mapPane].join(" ")} aria-labelledby="map-heading">
          <div className={styles.header}>
            <h2 id="map-heading">{t("bodymap.title")}</h2>
            <ViewToggle view={view} onChange={changeView} />
          </div>
          <BodyMap
            view={view}
            markers={markers}
            selectedZone={placing ? (point?.zone ?? zone?.code) : zone?.code}
            onSelectZone={setZone}
            onPlace={onPlace}
            placing={placing}
            onSelectMarker={(id) => void navigate(`/lesions/${id}`)}
          />
          <p className="text-secondary" role="status">
            {placing
              ? point
                ? t("lesions.placed")
                : zone
                  ? t("lesions.placingSpot", { zone: t(`zones.${zone.code}`, { defaultValue: zone.name }) })
                  : t("lesions.placingHint")
              : zone
                ? t("bodymap.selected", {
                    zone: t(`zones.${zone.code}`, { defaultValue: zone.name }),
                    view: t(`bodymap.views.${view}`),
                  })
                : t("bodymap.hint")}
          </p>
          {canEdit && !placing && (
            <div>
              <Button onClick={() => setPlacing(true)}>{t("lesions.add")}</Button>
            </div>
          )}
          {placing && !point && (
            <div>
              <Button variant="quiet" onClick={cancelPlacing}>
                {t("common.cancel")}
              </Button>
            </div>
          )}
          {placing && point && (
            <NewLesionForm
              point={point}
              view={view}
              pending={create.isPending}
              error={create.error?.message}
              onCancel={cancelPlacing}
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
        </section>

        <div className={styles.detailPane}>
          <section className={styles.mapSection} aria-labelledby="marks-heading">
            <h2 id="marks-heading">{t("lesions.title")}</h2>
            {lesions.error && <Notice kind="error">{lesions.error.message}</Notice>}
            {lesions.data && lesions.data.length === 0 && (
              <EmptyState
                title={t("lesions.emptyTitle")}
                text={canEdit ? t("lesions.emptyTextEdit") : t("lesions.emptyTextView")}
              />
            )}
            {lesions.data && lesions.data.length > 0 && <LesionList lesions={lesions.data} />}
          </section>

          {person.data && (
            <div className={styles.tools}>
              {(canEdit || (appointments.data?.length ?? 0) > 0) && (
                <Disclosure
                  id="appointments"
                  title={t("appointments.sectionTitle")}
                  hint={t("appointments.hint")}
                  defaultOpen={appointmentAhead}
                >
                  <PrepareAppointment personId={personId} canEdit={canEdit} embedded />
                </Disclosure>
              )}
              {(canEdit || (sessions.data?.length ?? 0) > 0) && (
                <Disclosure
                  id="sessions"
                  title={t("sessions.title")}
                  hint={t("sessions.hint")}
                  defaultOpen={sessionOpen}
                >
                  <SessionsSection personId={personId} canEdit={canEdit} embedded />
                </Disclosure>
              )}
              <Disclosure id="calendar" title={t("calendar.title")} hint={t("calendar.hint")}>
                <CalendarLink personId={personId} embedded />
              </Disclosure>
              <Disclosure id="reports" title={t("reports.title")} hint={t("reports.hint")}>
                <Reports
                  personId={personId}
                  embedded
                  titleOf={(id) => {
                    const lesion = lesions.data?.find((item) => item.id === id);
                    return lesion ? lesionTitle(lesion, t) : t("reports.deletedMark");
                  }}
                  marks={(lesions.data ?? []).map((lesion) => ({
                    id: lesion.id,
                    title: lesionTitle(lesion, t),
                  }))}
                />
              </Disclosure>
              {person.data.my_role === "owner" && (
                <Disclosure id="profile" title={t("persons.profileTitle")} hint={t("persons.profileHint")}>
                  <div className={styles.mapSection}>
                    <label className={styles.switchRow}>
                      <input
                        type="checkbox"
                        checked={person.data.experimental_analysis}
                        aria-describedby="experimental-hint"
                        onChange={(e) => updatePerson.mutate({ experimental_analysis: e.target.checked })}
                      />
                      {t("persons.experimental")}
                    </label>
                    <p id="experimental-hint" className="text-secondary">
                      {t("persons.experimentalHint")}
                    </p>
                    {updatePerson.error && <Notice kind="error">{updatePerson.error.message}</Notice>}
                    {usage.data && (
                      <p className="text-secondary">
                        {t("data.usage", {
                          count: usage.data.images,
                          size: formatBytes(usage.data.bytes, i18n.resolvedLanguage ?? "en"),
                        })}
                      </p>
                    )}
                    {usage.data?.over_quota && <Notice kind="attention">{t("data.overQuota")}</Notice>}
                    <ExportForm personId={personId} label={t("data.exportPerson")} />
                    <PurgePerson personId={personId} name={person.data.display_name} />
                  </div>
                </Disclosure>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
