import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { PhotoGallery } from "@/features/images/PhotoGallery";
import {
  SYMPTOMS,
  useDeleteObservation,
  useLesion,
  useObservation,
  useUpdateObservation,
  useUploadObservationImage,
  type Symptom,
} from "@/lib/lesions";
import { usePerson } from "@/lib/persons";
import { lesionTitle } from "./lesionName";
import styles from "./lesions.module.css";

export function ObservationPage() {
  const { observationId = "" } = useParams();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const observation = useObservation(observationId);
  const lesionId = observation.data?.lesion_id ?? "";
  const lesion = useLesion(lesionId);
  const person = usePerson(lesion.data?.person_id ?? "");
  const update = useUpdateObservation(observationId);
  const remove = useDeleteObservation(observationId, lesionId);
  const upload = useUploadObservationImage(observationId, lesionId);
  const [notes, setNotes] = useState("");
  const [symptoms, setSymptoms] = useState<Symptom[]>([]);
  const [dirty, setDirty] = useState(false);
  const canEdit = person.data?.my_role === "owner" || person.data?.my_role === "manager";
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, {
    dateStyle: "long",
    timeStyle: "short",
  });

  useEffect(() => {
    if (observation.data && !dirty) {
      setNotes(observation.data.notes ?? "");
      setSymptoms(observation.data.symptoms as Symptom[]);
    }
  }, [observation.data, dirty]);

  if (observation.error) return <Notice kind="error">{observation.error.message}</Notice>;
  if (!observation.data) return <p className="text-secondary">…</p>;
  const data = observation.data;

  function toggle(symptom: Symptom, checked: boolean) {
    setDirty(true);
    setSymptoms((current) => (checked ? [...current, symptom] : current.filter((s) => s !== symptom)));
  }

  function save() {
    update.mutate({ notes: notes.trim() || null, symptoms }, { onSuccess: () => setDirty(false) });
  }

  return (
    <div className={styles.page}>
      <p>
        <Link to={`/lesions/${data.lesion_id}`}>
          {lesion.data ? t("observations.backTo", { lesion: lesionTitle(lesion.data, t) }) : t("common.back")}
        </Link>
      </p>
      <header className={styles.header}>
        <h1 className="numeric">{dateFormat.format(new Date(data.captured_at))}</h1>
      </header>

      <section className={styles.section} aria-labelledby="photos-heading">
        <h2 id="photos-heading">{t("observations.photos")}</h2>
        <PhotoGallery images={data.images} canEdit={canEdit} upload={upload} />
      </section>

      <section className={styles.section} aria-labelledby="notes-heading">
        <h2 id="notes-heading">{t("observations.yourNotes")}</h2>
        <p className="text-secondary">{t("observations.notesHint")}</p>
        <div className={styles.checks}>
          {SYMPTOMS.map((symptom) => (
            <label key={symptom}>
              <input
                type="checkbox"
                checked={symptoms.includes(symptom)}
                disabled={!canEdit}
                onChange={(e) => toggle(symptom, e.target.checked)}
              />
              {t(`observations.symptoms.${symptom}`)}
            </label>
          ))}
        </div>
        <label>
          <span className="text-secondary">{t("observations.notes")}</span>
          <textarea
            className={styles.textarea}
            value={notes}
            readOnly={!canEdit}
            maxLength={4000}
            onChange={(e) => {
              setDirty(true);
              setNotes(e.target.value);
            }}
          />
        </label>
        {update.error && <Notice kind="error">{update.error.message}</Notice>}
        {canEdit && (
          <div className={styles.actions}>
            <Button onClick={save} disabled={!dirty || update.isPending}>
              {update.isPending ? t("common.working") : t("common.save")}
            </Button>
            <Button
              variant="danger"
              disabled={remove.isPending}
              onClick={() =>
                remove.mutate(undefined, { onSuccess: () => void navigate(`/lesions/${data.lesion_id}`) })
              }
            >
              {t("observations.delete")}
            </Button>
          </div>
        )}
      </section>
    </div>
  );
}
