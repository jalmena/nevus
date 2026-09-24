import { useRef, useState, type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";
import { Button } from "@/design-system/components/Button";
import { BodyMap } from "@/features/bodymap/BodyMap";
import { ViewToggle } from "@/features/bodymap/ViewToggle";
import { type View, type Zone } from "@/features/bodymap/zones";
import { EmptyState } from "@/design-system/components/EmptyState";
import { Notice } from "@/design-system/components/Notice";
import {
  imageUrl,
  useDeleteImage,
  useImages,
  useUploadImage,
  type ImageOut,
  type ImageRole,
} from "@/lib/images";
import { usePerson } from "@/lib/persons";
import styles from "./persons.module.css";

const ROLES: ImageRole[] = ["close_up", "with_reference", "overview", "other"];

export function PersonPage() {
  const { personId = "" } = useParams();
  const { t, i18n } = useTranslation();
  const person = usePerson(personId);
  const images = useImages(personId);
  const upload = useUploadImage(personId);
  const remove = useDeleteImage(personId);
  const [role, setRole] = useState<ImageRole>("close_up");
  const [open, setOpen] = useState<ImageOut | null>(null);
  const [view, setView] = useState<View>("front");
  const [zone, setZone] = useState<Zone | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const canEdit = person.data?.my_role === "owner" || person.data?.my_role === "manager";

  function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) upload.mutate({ file, role });
  }

  function show(image: ImageOut) {
    setOpen(image);
    dialog.current?.showModal();
  }

  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, {
    dateStyle: "medium",
    timeStyle: "short",
  });

  return (
    <div className={styles.page}>
      <p>
        <Link to="/">{t("common.back")}</Link>
      </p>
      <header className={styles.header}>
        <h1>{person.data?.display_name ?? "…"}</h1>
        {person.data && <span className="text-secondary">{t(`persons.role.${person.data.my_role}`)}</span>}
      </header>
      {person.error && <Notice kind="error">{person.error.message}</Notice>}

      <section className={styles.mapSection} aria-labelledby="map-heading">
        <div className={styles.header}>
          <h2 id="map-heading">{t("bodymap.title")}</h2>
          <ViewToggle
            view={view}
            onChange={(next) => {
              setView(next);
              setZone(null);
            }}
          />
        </div>
        <BodyMap view={view} selectedZone={zone?.code} onSelectZone={setZone} />
        <p className="text-secondary">
          {zone
            ? t("bodymap.selected", {
                zone: t(`zones.${zone.code}`, { defaultValue: zone.name }),
                view: t(`bodymap.views.${view}`),
              })
            : t("bodymap.hint")}
        </p>
      </section>

      {canEdit && (
        <section className={styles.upload} aria-labelledby="upload-heading">
          <h2 id="upload-heading">{t("images.addPhoto")}</h2>
          <div className={styles.roleRow}>
            <label>
              {t("images.role")}{" "}
              <select value={role} onChange={(e) => setRole(e.target.value as ImageRole)}>
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {t(`images.roles.${r}`)}
                  </option>
                ))}
              </select>
            </label>
            <Button className={styles.fileButton} disabled={upload.isPending}>
              {upload.isPending ? t("images.uploading") : t("images.takePhoto")}
              <input
                type="file"
                accept="image/*"
                capture="environment"
                onChange={onFile}
                aria-label={t("images.takePhoto")}
              />
            </Button>
            <Button variant="secondary" className={styles.fileButton} disabled={upload.isPending}>
              {t("images.chooseFile")}
              <input type="file" accept="image/*" onChange={onFile} aria-label={t("images.chooseFile")} />
            </Button>
          </div>
          <p className="text-secondary">{t("images.privacyNote")}</p>
          {upload.error && <Notice kind="error">{upload.error.message}</Notice>}
          {upload.isSuccess && <Notice kind="success">{t("images.uploaded")}</Notice>}
        </section>
      )}

      {images.data && images.data.length === 0 && (
        <EmptyState
          title={t("images.emptyTitle")}
          text={canEdit ? t("images.emptyTextEdit") : t("images.emptyTextView")}
        />
      )}
      <ul className={styles.gallery}>
        {images.data?.map((image) => (
          <li key={image.id}>
            <button
              type="button"
              className={styles.thumb}
              onClick={() => show(image)}
              aria-label={t("images.open")}
            >
              <img
                src={imageUrl(image.id, "thumb")}
                alt={t("images.alt", {
                  role: t(`images.roles.${image.role}`),
                  date: image.captured_at ? dateFormat.format(new Date(image.captured_at)) : "",
                })}
                width={image.renditions.find((r) => r.kind === "thumb")?.width}
                height={image.renditions.find((r) => r.kind === "thumb")?.height}
                loading="lazy"
                className={styles.thumb}
              />
            </button>
          </li>
        ))}
      </ul>

      <dialog ref={dialog} className={styles.preview} onClose={() => setOpen(null)}>
        {open && (
          <>
            <img src={imageUrl(open.id, "preview")} alt={t(`images.roles.${open.role}`)} />
            <div className={styles.previewBar}>
              <span className="numeric">
                {open.captured_at ? dateFormat.format(new Date(open.captured_at)) : t("images.noDate")} ·{" "}
                {open.width}×{open.height}
              </span>
              <span>
                {canEdit && (
                  <Button
                    variant="danger"
                    onClick={() => remove.mutate(open.id, { onSuccess: () => dialog.current?.close() })}
                    disabled={remove.isPending}
                  >
                    {t("images.delete")}
                  </Button>
                )}{" "}
                <Button variant="secondary" onClick={() => dialog.current?.close()}>
                  {t("common.close")}
                </Button>
              </span>
            </div>
          </>
        )}
      </dialog>
    </div>
  );
}
