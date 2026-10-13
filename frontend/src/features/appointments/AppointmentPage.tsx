import { Camera, Check, Pencil, Trash2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";
import { Button } from "@/design-system/components/Button";
import { IconButton } from "@/design-system/components/IconButton";
import { Notice } from "@/design-system/components/Notice";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Row, RowList } from "@/design-system/components/Row";
import { Section } from "@/design-system/components/Section";
import { Select } from "@/design-system/components/Select";
import { Sheet } from "@/design-system/components/Sheet";
import { TextField } from "@/design-system/components/TextField";
import { zoneName } from "@/features/lesions/lesionName";
import { personRail } from "@/features/persons/personRail";
import { shortDate } from "@/lib/dates";
import { useConfirm } from "@/lib/confirm/ConfirmProvider";
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
  const confirm = useConfirm();
  const appointment = useAppointment(appointmentId);
  const personId = appointment.data?.person_id ?? "";
  const reports = useReports(personId);
  const start = useStartVisit();
  const update = useUpdateAppointment(appointmentId);
  const remove = useDeleteAppointment();
  const makeReport = useVisitReport(appointmentId, personId);
  const [editing, setEditing] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [language, setLanguage] = useState<ReportLanguage>(i18n.resolvedLanguage === "es" ? "es" : "en");
  const [paper, setPaper] = useState<Paper>("a4");
  const locale = i18n.resolvedLanguage ?? "en";

  if (appointment.error) return <Notice kind="error">{appointment.error.message}</Notice>;
  if (!appointment.data) return <p className="text-secondary">…</p>;
  const data = appointment.data;
  const days = daysUntil(data.date);
  const pending = data.checklist.filter((item) => item.state !== "photographed");
  const done = data.checklist.filter((item) => item.state === "photographed");
  const report = reports.data?.find((item) => item.id === data.report_id);
  const title = (item: ChecklistItem) => item.label ?? zoneName(item.zone, t);
  const when =
    days === 0
      ? t("appointments.today")
      : days > 0
        ? t("appointments.inDays", { count: days })
        : t("appointments.daysAgo", { count: -days });

  function photograph(item: ChecklistItem) {
    start.mutate(item.lesion_id, { onSuccess: (visit) => void navigate(`/observations/${visit.id}`) });
  }

  const reportStatus = report
    ? report.status === "ready"
      ? t("reports.download", { count: report.pages ?? 0, size: formatBytes(report.bytes ?? 0, locale) })
      : report.status === "failed"
        ? (report.error ?? t("reports.failed"))
        : t("reports.making")
    : t("appointments.reportNotMade");

  return (
    <div className={styles.page}>
      <PageHeader
        back={{ to: `/persons/${data.person_id}`, label: data.person_name }}
        title={t("appointments.title", { date: shortDate(locale, data.date) })}
        meta={[when, t("appointments.progress", { done: done.length, total: data.checklist.length })]}
        rail={personRail(t, data.person_id, data.person_name)}
        menu={
          data.can_edit
            ? [
                { label: t("appointments.edit"), icon: <Pencil />, onSelect: () => setEditing(true) },
                {
                  label: t("appointments.delete"),
                  icon: <Trash2 />,
                  danger: true,
                  onSelect: () => {
                    void confirm({
                      title: t("appointments.deleteQuestion"),
                      text: t("appointments.deleteNote"),
                      action: t("appointments.delete"),
                      danger: true,
                    }).then(
                      (yes) =>
                        yes &&
                        remove.mutate(data.id, {
                          onSuccess: () => void navigate(`/persons/${data.person_id}`),
                        }),
                    );
                  },
                },
              ]
            : []
        }
      >
        {data.notes && <p className={styles.notes}>{data.notes}</p>}
      </PageHeader>
      {(start.error ?? remove.error) && (
        <Notice kind="error">{(start.error ?? remove.error)?.message}</Notice>
      )}

      <Section title={t("appointments.toPhotograph")}>
        {pending.length === 0 ? (
          <p className="text-secondary">{t("appointments.allDone")}</p>
        ) : (
          <RowList>
            {pending.map((item) => (
              <Row
                key={item.lesion_id}
                to={`/lesions/${item.lesion_id}`}
                title={title(item)}
                meta={
                  item.state === "never_photographed"
                    ? t("appointments.never")
                    : t("appointments.dueBy", {
                        date: shortDate(locale, item.next_due_on ?? data.date),
                      })
                }
                trailing={
                  data.can_edit ? (
                    <IconButton
                      label={t("appointments.photograph")}
                      icon={<Camera />}
                      showLabel="desktop"
                      variant="secondary"
                      onClick={() => photograph(item)}
                      disabled={start.isPending}
                    />
                  ) : undefined
                }
              />
            ))}
          </RowList>
        )}
        {done.length > 0 && (
          <RowList label={t("appointments.photographed")}>
            {done.map((item) => (
              <Row
                key={item.lesion_id}
                to={`/lesions/${item.lesion_id}`}
                leading={<Check className={styles.tick} />}
                title={title(item)}
                meta={
                  item.last_observed_at
                    ? t("appointments.photographedOn", {
                        date: shortDate(locale, item.last_observed_at),
                      })
                    : ""
                }
              />
            ))}
          </RowList>
        )}
      </Section>

      <Section title={t("appointments.reportTitle")}>
        <RowList>
          <Row
            onClick={() => setReportOpen(true)}
            title={t("appointments.reportTitle")}
            meta={reportStatus}
            trailing={
              report?.status === "ready" && report.download_url ? (
                <a
                  href={report.download_url}
                  download
                  className={styles.iconLink}
                  aria-label={t("reports.download", {
                    count: report.pages ?? 0,
                    size: formatBytes(report.bytes ?? 0, locale),
                  })}
                  onClick={(event) => event.stopPropagation()}
                >
                  <Camera aria-hidden="true" style={{ display: "none" }} />
                  {t("reports.download", {
                    count: report.pages ?? 0,
                    size: formatBytes(report.bytes ?? 0, locale),
                  })}
                </a>
              ) : undefined
            }
            chevron={report?.status !== "ready"}
          />
        </RowList>
        {makeReport.error && <Notice kind="error">{makeReport.error.message}</Notice>}
      </Section>

      <Sheet open={reportOpen} title={t("appointments.reportOptions")} onClose={() => setReportOpen(false)}>
        <form
          className={styles.editForm}
          onSubmit={(event) => {
            event.preventDefault();
            makeReport.mutate({ language, paper }, { onSuccess: () => setReportOpen(false) });
          }}
        >
          <p className="text-secondary">{t("appointments.reportIntro")}</p>
          <Select
            label={t("reports.language")}
            value={language}
            onChange={(e) => setLanguage(e.target.value as ReportLanguage)}
            options={[
              { value: "en", label: t("languages.en") },
              { value: "es", label: t("languages.es") },
            ]}
          />
          <Select
            label={t("reports.paper")}
            value={paper}
            onChange={(e) => setPaper(e.target.value as Paper)}
            options={[
              { value: "a4", label: "A4" },
              { value: "letter", label: t("reports.letter") },
            ]}
          />
          <div className={styles.actions}>
            <Button type="button" variant="quiet" onClick={() => setReportOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={makeReport.isPending}>
              {data.report_id ? t("appointments.reportAgain") : t("appointments.reportMake")}
            </Button>
          </div>
        </form>
      </Sheet>
      <Sheet open={editing} title={t("appointments.edit")} onClose={() => setEditing(false)}>
        <EditAppointment
          date={data.date}
          notes={data.notes}
          pending={update.isPending}
          error={update.error?.message}
          onCancel={() => setEditing(false)}
          onSave={(body) => update.mutate(body, { onSuccess: () => setEditing(false) })}
        />
      </Sheet>
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
        <Button type="button" variant="quiet" onClick={onCancel}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" disabled={pending || !value}>
          {t("common.save")}
        </Button>
      </div>
    </form>
  );
}
