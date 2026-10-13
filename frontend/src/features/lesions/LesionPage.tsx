import { Bell, BellOff, Clock, Columns2, FileText, Pencil, Trash2, TriangleAlert } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";
import type { MenuItem } from "@/design-system/components/Menu";
import { Button } from "@/design-system/components/Button";
import { EmptyState } from "@/design-system/components/EmptyState";
import { Notice } from "@/design-system/components/Notice";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Row, RowList } from "@/design-system/components/Row";
import { Section } from "@/design-system/components/Section";
import { Select } from "@/design-system/components/Select";
import { Sheet } from "@/design-system/components/Sheet";
import { StatusChip } from "@/design-system/components/StatusChip";
import { TextArea } from "@/design-system/components/TextArea";
import { TextField } from "@/design-system/components/TextField";
import { QuickVisit } from "@/features/capture/QuickVisit";
import { SizeChart } from "@/features/measure/SizeChart";
import { Sightings } from "@/features/sessions/Sightings";
import { useSession } from "@/lib/auth/session";
import { useConfirm } from "@/lib/confirm/ConfirmProvider";
import { imageUrl } from "@/lib/images";
import {
  INTERVALS,
  useCreateObservation,
  useDeleteLesion,
  useLesion,
  useObservations,
  useUpdateLesion,
} from "@/lib/lesions";
import { formatDelta, formatMm } from "@/lib/measurements";
import { usePerson } from "@/lib/persons";
import { useSnooze } from "@/lib/reminders";
import { lesionTitle, zoneName } from "./lesionName";
import styles from "./lesions.module.css";

/** One mark: what it is and where, its latest size, and its visits newest first. */
export function LesionPage() {
  const { lesionId = "" } = useParams();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const confirm = useConfirm();
  const lesion = useLesion(lesionId);
  const person = usePerson(lesion.data?.person_id ?? "");
  const observations = useObservations(lesionId);
  const createVisit = useCreateObservation(lesionId);
  const update = useUpdateLesion(lesionId);
  const remove = useDeleteLesion(lesionId, lesion.data?.person_id ?? "");
  const snooze = useSnooze(lesionId);
  const [editing, setEditing] = useState(false);
  const [quick, setQuick] = useState(false);
  const canEdit = person.data?.my_role === "owner" || person.data?.my_role === "manager";
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "long" });
  const shortDate = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium" });
  const session = useSession();
  const showUncertainty = session.data?.user.show_uncertainty ?? true;
  const locale = i18n.resolvedLanguage ?? "en";

  function newVisit() {
    if (!navigator.onLine) {
      setQuick(true); // no connection: record the visit on this device and upload it later
      return;
    }
    createVisit.mutate(
      { captured_tz: Intl.DateTimeFormat().resolvedOptions().timeZone },
      {
        onSuccess: (observation) => void navigate(`/observations/${observation.id}`),
        onError: (error) => {
          if (error instanceof TypeError) setQuick(true); // the network went away mid-request
        },
      },
    );
  }

  if (lesion.error) return <Notice kind="error">{lesion.error.message}</Notice>;
  if (!lesion.data) return <p className="text-secondary">…</p>;
  const data = lesion.data;
  const title = lesionTitle(data, t);
  const photographedVisits = observations.data?.filter((visit) => visit.images.length > 0).length ?? 0;
  const interval = t(`lesions.intervals.${data.interval_days}`, {
    defaultValue: t("lesions.days", { count: data.interval_days }),
  });

  const menu: MenuItem[] = [];
  if (canEdit) menu.push({ label: t("lesions.edit"), icon: <Pencil />, onSelect: () => setEditing(true) });
  if (canEdit && data.due && !data.snoozed_until) {
    menu.push({ label: t("reminders.snoozeWeekMenu"), icon: <BellOff />, onSelect: () => snooze.mutate(7) });
    menu.push({
      label: t("reminders.snoozeMonthMenu"),
      icon: <BellOff />,
      onSelect: () => snooze.mutate(30),
    });
  }
  if (canEdit && data.snoozed_until)
    menu.push({ label: t("reminders.unsnooze"), icon: <Bell />, onSelect: () => snooze.mutate(null) });
  menu.push({
    label: t("reports.title"),
    icon: <FileText />,
    onSelect: () => void navigate(`/lesions/${data.id}/reports`),
  });
  if (canEdit)
    menu.push({
      label: t("lesions.delete"),
      icon: <Trash2 />,
      danger: true,
      onSelect: () => {
        void confirm({
          title: t("lesions.deleteQuestion"),
          text: t("lesions.deleteNote"),
          action: t("lesions.delete"),
          danger: true,
        }).then(
          (yes) =>
            yes && remove.mutate(undefined, { onSuccess: () => void navigate(`/persons/${data.person_id}`) }),
        );
      },
    });

  return (
    <div className={styles.page}>
      <PageHeader
        back={{ to: `/persons/${data.person_id}`, label: person.data?.display_name ?? t("shell.persons") }}
        title={title}
        meta={[
          zoneName(data.location.zone, t),
          t(`bodymap.views.${data.location.view}`),
          t(`lesions.types.${data.type}`),
          data.snoozed_until
            ? t("reminders.snoozedMeta", { date: shortDate.format(new Date(data.snoozed_until)) })
            : data.next_due_on && !data.due
              ? t("lesions.nextCheck", { date: shortDate.format(new Date(data.next_due_on)) })
              : null,
          t("lesions.every", { interval }),
        ]}
        chip={
          data.due ? (
            <StatusChip kind="due" icon={<Clock />}>
              {t("lesions.dueNow")}
            </StatusChip>
          ) : data.status !== "active" ? (
            <StatusChip>{t(`lesions.statuses.${data.status}`)}</StatusChip>
          ) : undefined
        }
        facts={[
          {
            label: t("lesions.latestSize"),
            value: data.latest_measurement
              ? formatMm(
                  data.latest_measurement.longest_mm,
                  data.latest_measurement.sigma_longest_mm,
                  locale,
                  showUncertainty,
                )
              : null,
          },
          {
            label: data.measurement_change
              ? t("lesions.sinceDate", { date: shortDate.format(new Date(data.measurement_change.since)) })
              : "",
            value: data.measurement_change ? (
              <>
                {formatDelta(
                  data.measurement_change.delta_mm,
                  data.measurement_change.sigma_mm,
                  locale,
                  showUncertainty,
                )}
                <span className={styles.factNote}>
                  {data.measurement_change.detectable
                    ? t("lesions.measuredChange")
                    : t("lesions.noDetectableChange")}
                </span>
              </>
            ) : null,
          },
        ]}
        actions={
          photographedVisits >= 2
            ? [
                {
                  key: "compare",
                  label: t("compare.open"),
                  icon: <Columns2 />,
                  to: `/lesions/${data.id}/compare`,
                },
              ]
            : []
        }
        primary={
          canEdit
            ? { label: t("observations.new"), onClick: newVisit, pending: createVisit.isPending }
            : undefined
        }
        menu={menu}
      >
        {data.notes && <p className={styles.notes}>{data.notes}</p>}
      </PageHeader>
      {(createVisit.error && !quick) || snooze.error || remove.error ? (
        <Notice kind="error">{(createVisit.error ?? snooze.error ?? remove.error)?.message}</Notice>
      ) : null}

      {observations.data && observations.data.length === 0 && (
        <EmptyState>{t("observations.emptyText")}</EmptyState>
      )}
      {observations.data && observations.data.length > 0 && (
        <Section title={t("observations.title")} className={styles.visits}>
          <RowList>
            {observations.data.map((visit) => (
              <Row
                key={visit.id}
                to={`/observations/${visit.id}`}
                title={
                  <span className="numeric">{dateFormat.format(new Date(visit.captured_local_date))}</span>
                }
                extra={
                  visit.images.length > 0 ? (
                    <span className={styles.visitThumbs}>
                      {visit.images.slice(0, 4).map((image) => (
                        <img key={image.id} src={imageUrl(image.id, "thumb")} alt="" loading="lazy" />
                      ))}
                    </span>
                  ) : undefined
                }
                meta={
                  <>
                    {[
                      t("observations.photoCount", { count: visit.images.length }),
                      ...visit.symptoms.map((symptom) => t(`observations.symptoms.${symptom}`)),
                    ].join(" · ")}
                    {visit.quality_flags.length > 0 && (
                      <span className={styles.qualityMeta}>
                        <TriangleAlert aria-hidden="true" /> {t("quality.short")}
                      </span>
                    )}
                  </>
                }
                chevron={false}
              />
            ))}
          </RowList>
        </Section>
      )}

      <SizeChart lesionId={data.id} />
      <Sightings lesionId={data.id} />

      <Sheet open={editing} title={t("lesions.edit")} onClose={() => setEditing(false)}>
        <EditLesionForm
          lesion={data}
          pending={update.isPending}
          error={update.error?.message}
          onCancel={() => setEditing(false)}
          onSubmit={(body) => update.mutate(body, { onSuccess: () => setEditing(false) })}
        />
      </Sheet>
      <Sheet open={quick} title={t("observations.new")} onClose={() => setQuick(false)}>
        <QuickVisit lesionId={data.id} lesionLabel={title} onDone={() => undefined} />
      </Sheet>
    </div>
  );
}

function EditLesionForm({
  lesion,
  pending,
  error,
  onCancel,
  onSubmit,
}: {
  lesion: ReturnType<typeof useLesion>["data"] & object;
  pending: boolean;
  error?: string;
  onCancel: () => void;
  onSubmit: (body: {
    label: string | null;
    type: "mole" | "other";
    status: "active" | "removed" | "resolved";
    first_noticed_on: string | null;
    interval_days: number;
    notes: string | null;
  }) => void;
}) {
  const { t } = useTranslation();
  const [label, setLabel] = useState(lesion.label ?? "");
  const [type, setType] = useState<"mole" | "other">(lesion.type as "mole" | "other");
  const [status, setStatus] = useState<"active" | "removed" | "resolved">(
    lesion.status as "active" | "removed" | "resolved",
  );
  const [firstNoticed, setFirstNoticed] = useState(lesion.first_noticed_on ?? "");
  const [interval, setInterval] = useState(lesion.interval_days);
  const [notes, setNotes] = useState(lesion.notes ?? "");

  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      label: label.trim() || null,
      type,
      status,
      first_noticed_on: firstNoticed || null,
      interval_days: interval,
      notes: notes.trim() || null,
    });
  }

  return (
    <form className={styles.form} onSubmit={submit}>
      <TextField
        label={t("lesions.label")}
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        maxLength={120}
      />
      <Select
        label={t("lesions.type")}
        value={type}
        onChange={(e) => setType(e.target.value as "mole" | "other")}
        options={[
          { value: "mole", label: t("lesions.types.mole") },
          { value: "other", label: t("lesions.types.other") },
        ]}
      />
      <Select
        label={t("lesions.status")}
        value={status}
        onChange={(e) => setStatus(e.target.value as "active" | "removed" | "resolved")}
        options={(["active", "removed", "resolved"] as const).map((value) => ({
          value,
          label: t(`lesions.statuses.${value}`),
        }))}
      />
      <TextField
        label={t("lesions.firstNoticed")}
        type="date"
        value={firstNoticed}
        onChange={(e) => setFirstNoticed(e.target.value)}
      />
      <Select
        label={t("lesions.interval")}
        value={String(interval)}
        onChange={(e) => setInterval(Number(e.target.value))}
        options={INTERVALS.map((days) => ({ value: String(days), label: t(`lesions.intervals.${days}`) }))}
      />
      <TextArea
        label={t("lesions.notes")}
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        maxLength={4000}
      />
      {error && <Notice kind="error">{error}</Notice>}
      <div className={styles.actions}>
        <Button type="button" variant="quiet" onClick={onCancel}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" disabled={pending}>
          {t("common.save")}
        </Button>
      </div>
    </form>
  );
}
