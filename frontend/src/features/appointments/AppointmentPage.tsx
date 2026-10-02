import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { TextField } from "@/design-system/components/TextField";
import { zoneName } from "@/features/lesions/lesionName";
import { formatBytes } from "@/lib/data";
import {
  daysUntil,
  useAppointment,
  useDeleteAppointment,
  useStartVisit,
  useUpdateAppointment,
  useVisitReport,
  type ChecklistItem,
} from "@/lib/appointments";
import { useReports, type Paper, type ReportLanguage } from "@/lib/reports";
import styles from "./appointments.module.css";

/** Getting ready for a clinician: photograph what is due by the date, then make the report to bring. */
export function AppointmentPage() {
  const { appointmentId = "" } = useParams();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const appointment = useAppointment(appointmentId);
  const personId = appointment.data?.person_id ?? "";
  const reports = useReports(personId);
  const start = useStartVisit();
  const update = useUpdateAppointment(appointmentId);
  const remove = useDeleteAppointment();
  const makeReport = useVisitReport(appointmentId, personId);
  const [editing, setEditing] = useState(false);
  const [language, setLanguage] = useState<ReportLanguage>(i18n.resolvedLanguage === "es" ? "es" : "en");
  const [paper, setPaper] = useState<Paper>("a4");
  const locale = i18n.resolvedLanguage ?? "en";
  const longDate = new Intl.DateTimeFormat(locale, { dateStyle: "full" });
  const shortDate = new Intl.DateTimeFormat(locale, { dateStyle: "medium" });

  if (appointment.error) return <Notice kind="error">{appointment.error.message}</Notice>;
  if (!appointment.data) return <p className="text-secondary">…</p>;
  const data = appointment.data;
  const days = daysUntil(data.date);
  const pending = data.checklist.filter((item) => item.state !== "photographed");
  const done = data.checklist.filter((item) => item.state === "photographed");
  const report = reports.data?.find((item) => item.id === data.report_id);
  const title = (item: ChecklistItem) => item.label ?? zoneName(item.zone, t);

  function photograph(item: ChecklistItem) {
    start.mutate(item.lesion_id, { onSuccess: (visit) => void navigate(`/observations/${visit.id}`) });
  }

  return (
    <div className={styles.page}>
      <p>
        <Link to={`/persons/${data.person_id}`}>{t("appointments.backTo", { name: data.person_name })}</Link>
      </p>
      <header>
        <h1>{t("appointments.title", { date: longDate.format(new Date(`${data.date}T12:00:00`)) })}</h1>
        <p className="text-secondary">
          {days === 0
            ? t("appointments.today")
            : days > 0
              ? t("appointments.inDays", { count: days })
              : t("appointments.daysAgo", { count: -days })}
        </p>
        {data.notes && <p className={styles.notes}>{data.notes}</p>}
      </header>

      {data.can_edit && !editing && (
        <div className={styles.actions}>
          <Button variant="secondary" onClick={() => setEditing(true)}>
            {t("appointments.edit")}
          </Button>
          <Button
            variant="quiet"
            onClick={() =>
              remove.mutate(data.id, { onSuccess: () => void navigate(`/persons/${data.person_id}`) })
            }
            disabled={remove.isPending}
          >
            {t("appointments.delete")}
          </Button>
        </div>
      )}
      {editing && (
        <EditAppointment
          date={data.date}
          notes={data.notes}
          pending={update.isPending}
          error={update.error?.message}
          onCancel={() => setEditing(false)}
          onSave={(body) => update.mutate(body, { onSuccess: () => setEditing(false) })}
        />
      )}

      <section className={styles.section} aria-labelledby="todo-heading">
        <h2 id="todo-heading">{t("appointments.toPhotograph")}</h2>
        <p className="text-secondary">
          {t("appointments.progress", { done: done.length, total: data.checklist.length })}
        </p>
        {pending.length === 0 ? (
          <Notice kind="success">{t("appointments.allDone")}</Notice>
        ) : (
          <ul className={styles.list}>
            {pending.map((item) => (
              <li key={item.lesion_id} className={styles.item}>
                <span className={styles.what}>
                  <Link to={`/lesions/${item.lesion_id}`}>{title(item)}</Link>
                  <span className="text-secondary">
                    {item.state === "never_photographed"
                      ? t("appointments.never")
                      : t("appointments.dueBy", {
                          date: shortDate.format(new Date(`${item.next_due_on ?? data.date}T12:00:00`)),
                        })}
                  </span>
                </span>
                {data.can_edit && (
                  <Button onClick={() => photograph(item)} disabled={start.isPending}>
                    {t("appointments.photograph")}
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
        {start.error && <Notice kind="error">{start.error.message}</Notice>}
        {done.length > 0 && (
          <>
            <h3 className={styles.subheading}>{t("appointments.photographed")}</h3>
            <ul className={styles.list}>
              {done.map((item) => (
                <li key={item.lesion_id} className={[styles.item, styles.done].join(" ")}>
                  <span className={styles.what}>
                    <Link to={`/lesions/${item.lesion_id}`}>{title(item)}</Link>
                    <span className="text-secondary">
                      {item.last_observed_at
                        ? t("appointments.photographedOn", {
                            date: shortDate.format(new Date(item.last_observed_at)),
                          })
                        : ""}
                    </span>
                  </span>
                  <span className={styles.tick} aria-hidden="true">
                    ✓
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className={styles.section} aria-labelledby="report-heading">
        <h2 id="report-heading">{t("appointments.reportTitle")}</h2>
        <p className="text-secondary">{t("appointments.reportIntro")}</p>
        <form
          className={styles.form}
          onSubmit={(event) => {
            event.preventDefault();
            makeReport.mutate({ language, paper });
          }}
        >
          <label className={styles.field}>
            <span>{t("reports.language")}</span>
            <select value={language} onChange={(e) => setLanguage(e.target.value as ReportLanguage)}>
              <option value="en">{t("languages.en")}</option>
              <option value="es">{t("languages.es")}</option>
            </select>
          </label>
          <label className={styles.field}>
            <span>{t("reports.paper")}</span>
            <select value={paper} onChange={(e) => setPaper(e.target.value as Paper)}>
              <option value="a4">A4</option>
              <option value="letter">{t("reports.letter")}</option>
            </select>
          </label>
          <Button type="submit" disabled={makeReport.isPending}>
            {data.report_id ? t("appointments.reportAgain") : t("appointments.reportMake")}
          </Button>
        </form>
        {makeReport.error && <Notice kind="error">{makeReport.error.message}</Notice>}
        {report && (
          <p>
            {report.status === "ready" && report.download_url ? (
              <a href={report.download_url} download>
                {t("reports.download", {
                  count: report.pages ?? 0,
                  size: formatBytes(report.bytes ?? 0, locale),
                })}
              </a>
            ) : report.status === "failed" ? (
              <span className={styles.failed}>{report.error ?? t("reports.failed")}</span>
            ) : (
              <span className="text-secondary" role="status">
                {t("reports.making")}
              </span>
            )}
          </p>
        )}
      </section>
    </div>
  );
}

function EditAppointment({
  date,
  notes,
  pending,
  error,
  onCancel,
  onSave,
}: {
  date: string;
  notes: string | null;
  pending: boolean;
  error?: string;
  onCancel: () => void;
  onSave: (body: { date: string; notes: string | null }) => void;
}) {
  const { t } = useTranslation();
  const [value, setValue] = useState(date);
  const [text, setText] = useState(notes ?? "");

  function submit(event: FormEvent) {
    event.preventDefault();
    onSave({ date: value, notes: text.trim() || null });
  }

  return (
    <form className={styles.editForm} onSubmit={submit}>
      <TextField
        label={t("appointments.date")}
        type="date"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        required
      />
      <TextField
        label={t("appointments.notes")}
        value={text}
        onChange={(e) => setText(e.target.value)}
        maxLength={2000}
      />
      {error && <Notice kind="error">{error}</Notice>}
      <div className={styles.actions}>
        <Button type="submit" disabled={pending || !value}>
          {t("common.save")}
        </Button>
        <Button type="button" variant="quiet" onClick={onCancel}>
          {t("common.cancel")}
        </Button>
      </div>
    </form>
  );
}
