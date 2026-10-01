import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";
import { Button } from "@/design-system/components/Button";
import { EmptyState } from "@/design-system/components/EmptyState";
import { Notice } from "@/design-system/components/Notice";
import { TextField } from "@/design-system/components/TextField";
import { imageUrl } from "@/lib/images";
import { useSession } from "@/lib/auth/session";
import { INTERVALS, useCreateObservation, useLesion, useObservations, useUpdateLesion } from "@/lib/lesions";
import { formatDelta, formatMm } from "@/lib/measurements";
import { usePerson } from "@/lib/persons";
import { DueBadge } from "./LesionList";
import { lesionTitle, locationLine } from "./lesionName";
import styles from "./lesions.module.css";

export function LesionPage() {
  const { lesionId = "" } = useParams();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const lesion = useLesion(lesionId);
  const person = usePerson(lesion.data?.person_id ?? "");
  const observations = useObservations(lesionId);
  const createVisit = useCreateObservation(lesionId);
  const update = useUpdateLesion(lesionId);
  const [editing, setEditing] = useState(false);
  const canEdit = person.data?.my_role === "owner" || person.data?.my_role === "manager";
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "long" });
  const session = useSession();
  const showUncertainty = session.data?.user.show_uncertainty ?? true;
  const locale = i18n.resolvedLanguage ?? "en";

  function newVisit() {
    createVisit.mutate(
      { captured_tz: Intl.DateTimeFormat().resolvedOptions().timeZone },
      { onSuccess: (observation) => void navigate(`/observations/${observation.id}`) },
    );
  }

  if (lesion.error) return <Notice kind="error">{lesion.error.message}</Notice>;
  if (!lesion.data) return <p className="text-secondary">…</p>;
  const data = lesion.data;

  return (
    <div className={styles.page}>
      <p>
        <Link to={`/persons/${data.person_id}`}>{t("lesions.backToPerson")}</Link>
      </p>
      <header className={styles.header}>
        <h1>{lesionTitle(data, t)}</h1>
        <DueBadge lesion={data} />
      </header>
      <p className="text-secondary">
        {locationLine(data, t)} · {t(`lesions.types.${data.type}`)}
      </p>
      <dl className={styles.facts}>
        <div>
          <dt>{t("lesions.firstNoticed")}</dt>
          <dd className="numeric">
            {data.first_noticed_on ? dateFormat.format(new Date(data.first_noticed_on)) : "—"}
          </dd>
        </div>
        <div>
          <dt>{t("lesions.interval")}</dt>
          <dd>
            {t(`lesions.intervals.${data.interval_days}`, {
              defaultValue: t("lesions.days", { count: data.interval_days }),
            })}
          </dd>
        </div>
        <div>
          <dt>{t("lesions.latestSize")}</dt>
          <dd className="numeric">
            {data.latest_measurement
              ? formatMm(
                  data.latest_measurement.longest_mm,
                  data.latest_measurement.sigma_longest_mm,
                  locale,
                  showUncertainty,
                )
              : "—"}
          </dd>
        </div>
        {data.measurement_change && (
          <div>
            <dt>
              {t("lesions.sinceDate", { date: dateFormat.format(new Date(data.measurement_change.since)) })}
            </dt>
            <dd className="numeric">
              {formatDelta(
                data.measurement_change.delta_mm,
                data.measurement_change.sigma_mm,
                locale,
                showUncertainty,
              )}{" "}
              ·{" "}
              {data.measurement_change.detectable
                ? t("lesions.measuredChange")
                : t("lesions.noDetectableChange")}
            </dd>
          </div>
        )}
        <div>
          <dt>{t("lesions.nextDue")}</dt>
          <dd className="numeric">
            {data.next_due_on ? dateFormat.format(new Date(data.next_due_on)) : "—"}
          </dd>
        </div>
      </dl>
      {data.notes && <p>{data.notes}</p>}

      {canEdit && (
        <div className={styles.actions}>
          <Button onClick={newVisit} disabled={createVisit.isPending}>
            {createVisit.isPending ? t("common.working") : t("observations.new")}
          </Button>
          <Button variant="secondary" onClick={() => setEditing((value) => !value)}>
            {editing ? t("common.cancel") : t("lesions.edit")}
          </Button>
        </div>
      )}
      {createVisit.error && <Notice kind="error">{createVisit.error.message}</Notice>}
      {editing && (
        <EditLesionForm
          lesion={data}
          pending={update.isPending}
          error={update.error?.message}
          onSubmit={(body) => update.mutate(body, { onSuccess: () => setEditing(false) })}
        />
      )}

      <section className={styles.section} aria-labelledby="visits-heading">
        <h2 id="visits-heading">{t("observations.title")}</h2>
        {observations.data && observations.data.length === 0 && (
          <EmptyState title={t("observations.emptyTitle")} text={t("observations.emptyText")} />
        )}
        <ol className={styles.timeline}>
          {observations.data?.map((visit) => (
            <li key={visit.id}>
              <Link to={`/observations/${visit.id}`} className={styles.visit}>
                <span className={styles.visitHead}>
                  <span className="numeric">{dateFormat.format(new Date(visit.captured_local_date))}</span>
                  <span className="text-secondary">
                    {t("observations.photoCount", { count: visit.images.length })}
                  </span>
                </span>
                {visit.images.length > 0 && (
                  <span className={styles.visitThumbs}>
                    {visit.images.slice(0, 4).map((image) => (
                      <img key={image.id} src={imageUrl(image.id, "thumb")} alt="" loading="lazy" />
                    ))}
                  </span>
                )}
                {visit.quality_flags.length > 0 && (
                  <span className={styles.chips}>
                    <span className={[styles.badge, styles.due].join(" ")}>{t("quality.short")}</span>
                  </span>
                )}
                {visit.symptoms.length > 0 && (
                  <span className={styles.chips}>
                    {visit.symptoms.map((symptom) => (
                      <span key={symptom} className={styles.badge}>
                        {t(`observations.symptoms.${symptom}`)}
                      </span>
                    ))}
                  </span>
                )}
                {visit.notes && <span className="text-secondary">{visit.notes}</span>}
              </Link>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

function EditLesionForm({
  lesion,
  pending,
  error,
  onSubmit,
}: {
  lesion: ReturnType<typeof useLesion>["data"] & object;
  pending: boolean;
  error?: string;
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
      <label className={styles.row}>
        <span>{t("lesions.type")}</span>
        <select value={type} onChange={(e) => setType(e.target.value as "mole" | "other")}>
          <option value="mole">{t("lesions.types.mole")}</option>
          <option value="other">{t("lesions.types.other")}</option>
        </select>
      </label>
      <label className={styles.row}>
        <span>{t("lesions.status")}</span>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value as "active" | "removed" | "resolved")}
        >
          {(["active", "removed", "resolved"] as const).map((value) => (
            <option key={value} value={value}>
              {t(`lesions.statuses.${value}`)}
            </option>
          ))}
        </select>
      </label>
      <TextField
        label={t("lesions.firstNoticed")}
        type="date"
        value={firstNoticed}
        onChange={(e) => setFirstNoticed(e.target.value)}
      />
      <label className={styles.row}>
        <span>{t("lesions.interval")}</span>
        <select value={interval} onChange={(e) => setInterval(Number(e.target.value))}>
          {INTERVALS.map((days) => (
            <option key={days} value={days}>
              {t(`lesions.intervals.${days}`)}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span className="text-secondary">{t("lesions.notes")}</span>
        <textarea
          className={styles.textarea}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          maxLength={4000}
        />
      </label>
      {error && <Notice kind="error">{error}</Notice>}
      <div className={styles.actions}>
        <Button type="submit" disabled={pending}>
          {t("common.save")}
        </Button>
      </div>
    </form>
  );
}
