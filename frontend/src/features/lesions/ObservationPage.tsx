import { Camera, Ruler, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";
import type { MenuItem } from "@/design-system/components/Menu";
import { Chip } from "@/design-system/components/Chip";
import { Notice } from "@/design-system/components/Notice";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Section } from "@/design-system/components/Section";
import { TextArea } from "@/design-system/components/TextArea";
import { PhotoGallery } from "@/features/images/PhotoGallery";
import { Proposals } from "@/features/measure/Proposals";
import { VisitMeasurements } from "@/features/measure/VisitMeasurements";
import { shortDate } from "@/lib/dates";
import { useConfirm } from "@/lib/confirm/ConfirmProvider";
import type { ImageRole } from "@/lib/images";
import {
  SYMPTOMS,
  useDeleteObservation,
  useLesion,
  useObservation,
  useObservations,
  useUpdateObservation,
  useUploadObservationImage,
  type Symptom,
} from "@/lib/lesions";
import { useVisitMeasurements } from "@/lib/measurements";
import { personRail } from "@/features/persons/personRail";
import { usePerson } from "@/lib/persons";
import { lesionTitle } from "./lesionName";
import styles from "./lesions.module.css";

/** One visit: the photographs, the measurement, what the person noticed. */
export function ObservationPage() {
  const { observationId = "" } = useParams();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const confirm = useConfirm();
  const observation = useObservation(observationId);
  const lesionId = observation.data?.lesion_id ?? "";
  const lesion = useLesion(lesionId);
  const visits = useObservations(lesionId);
  const person = usePerson(lesion.data?.person_id ?? "");
  const measurements = useVisitMeasurements(observationId);
  const update = useUpdateObservation(observationId);
  const remove = useDeleteObservation(observationId, lesionId);
  const upload = useUploadObservationImage(observationId, lesionId);
  const camera = useRef<HTMLInputElement>(null);
  const [role, setRole] = useState<ImageRole>("close_up");
  const [adding, setAdding] = useState(false);
  const [notes, setNotes] = useState("");
  const [symptoms, setSymptoms] = useState<Symptom[]>([]);
  const [dirty, setDirty] = useState(false);
  const canEdit = person.data?.my_role === "owner" || person.data?.my_role === "manager";
  const timeFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { timeStyle: "short" });

  useEffect(() => {
    if (observation.data && !dirty) {
      setNotes(observation.data.notes ?? "");
      setSymptoms(observation.data.symptoms as Symptom[]);
    }
  }, [observation.data, dirty]);

  if (observation.error) return <Notice kind="error">{observation.error.message}</Notice>;
  if (!observation.data) return <p className="text-secondary">…</p>;
  const data = observation.data;
  const markTitle = lesion.data ? lesionTitle(lesion.data, t) : "…";
  const previous = (visits.data ?? [])
    .filter(
      (visit) => visit.id !== data.id && visit.captured_at < data.captured_at && visit.images.length > 0,
    )
    .sort((a, b) => b.captured_at.localeCompare(a.captured_at))[0];
  const previousImageId =
    previous?.images.find((image) => image.role === "close_up")?.id ?? previous?.images[0]?.id ?? null;
  const measured = (measurements.data?.length ?? 0) > 0;
  const firstImage = data.images.find((image) => image.role !== "overview") ?? data.images[0];
  const measureUrl = (imageId: string) => `/observations/${data.id}/measure/${imageId}`;

  function toggle(symptom: Symptom) {
    setDirty(true);
    setSymptoms((current) =>
      current.includes(symptom) ? current.filter((s) => s !== symptom) : [...current, symptom],
    );
  }

  function save() {
    update.mutate({ notes: notes.trim() || null, symptoms }, { onSuccess: () => setDirty(false) });
  }

  const primary = !canEdit
    ? undefined
    : data.images.length === 0
      ? { label: t("images.takePhoto"), onClick: () => camera.current?.click(), pending: upload.isPending }
      : dirty
        ? { label: t("common.save"), onClick: save, pending: update.isPending }
        : !measured && firstImage
          ? { label: t("measure.title"), onClick: () => void navigate(measureUrl(firstImage.id)) }
          : undefined;

  const menu: MenuItem[] = [];
  if (canEdit) {
    menu.push({ label: t("images.addPhoto"), icon: <Camera />, onSelect: () => setAdding(true) });
    if (data.images.length > 1)
      data.images.forEach((image, index) =>
        menu.push({
          label: t("measure.measurePhotoN", { n: index + 1 }),
          icon: <Ruler />,
          onSelect: () => void navigate(measureUrl(image.id)),
        }),
      );
    menu.push({
      label: t("observations.delete"),
      icon: <Trash2 />,
      danger: true,
      onSelect: () => {
        void confirm({
          title: t("observations.deleteQuestion"),
          text: t("observations.deleteNote"),
          action: t("observations.delete"),
          danger: true,
        }).then(
          (yes) =>
            yes && remove.mutate(undefined, { onSuccess: () => void navigate(`/lesions/${data.lesion_id}`) }),
        );
      },
    });
  }

  return (
    <div className={[styles.page, "page-wide"].join(" ")}>
      <PageHeader
        back={{ to: `/lesions/${data.lesion_id}`, label: markTitle }}
        title={shortDate(i18n.resolvedLanguage, data.captured_at)}
        meta={[timeFormat.format(new Date(data.captured_at)), markTitle, person.data?.display_name ?? null]}
        primary={primary}
        menu={menu}
        rail={lesion.data ? personRail(t, lesion.data.person_id, person.data?.display_name) : undefined}
      />
      {remove.error && <Notice kind="error">{remove.error.message}</Notice>}

      <div className={styles.layout}>
        <div className={styles.photoPane}>
          <PhotoGallery
            images={data.images}
            canEdit={canEdit}
            upload={upload}
            previousImageId={previousImageId}
            role={role}
            onRole={setRole}
            cameraRef={camera}
            addOpen={adding}
            onAddOpen={setAdding}
            quality={{
              flags: data.quality_flags,
              checking: data.images.some((image) => !image.quality_checked_at),
            }}
          />
        </div>

        <div className={styles.dataPane}>
          <Proposals observationId={data.id} images={data.images} canEdit={canEdit} />
          <VisitMeasurements observationId={data.id} images={data.images} canEdit={canEdit} />

          <Section title={t("observations.notes")}>
            <div className={styles.chips}>
              {SYMPTOMS.map((symptom) => (
                <Chip
                  key={symptom}
                  pressed={symptoms.includes(symptom)}
                  disabled={!canEdit}
                  onClick={() => toggle(symptom)}
                >
                  {t(`observations.symptoms.${symptom}`)}
                </Chip>
              ))}
            </div>
            <TextArea
              label={t("observations.notes")}
              labelHidden
              placeholder={t("observations.notesPlaceholder")}
              value={notes}
              readOnly={!canEdit}
              maxLength={4000}
              onChange={(e) => {
                setDirty(true);
                setNotes(e.target.value);
              }}
            />
            {update.error && <Notice kind="error">{update.error.message}</Notice>}
            {update.isSuccess && !dirty && (
              <p className="text-secondary" role="status">
                {t("common.saved")}
              </p>
            )}
          </Section>
        </div>
      </div>
    </div>
  );
}
