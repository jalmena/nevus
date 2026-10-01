import { useRef, useState, type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { IMAGE_ROLES, imageUrl, useDeleteImage, type ImageOut, type ImageRole } from "@/lib/images";
import styles from "./PhotoGallery.module.css";

interface Props {
  images: ImageOut[];
  canEdit: boolean;
  upload?: {
    mutate: (input: { file: File; role: ImageRole }) => void;
    isPending: boolean;
    error: Error | null;
  };
}

/** Thumbnails with a preview dialog, plus the camera and file buttons when the viewer may add photos. */
export function PhotoGallery({ images, canEdit, upload }: Props) {
  const { t, i18n } = useTranslation();
  const remove = useDeleteImage();
  const [role, setRole] = useState<ImageRole>("close_up");
  const [open, setOpen] = useState<ImageOut | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, {
    dateStyle: "medium",
    timeStyle: "short",
  });

  function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file && upload) upload.mutate({ file, role });
  }

  function show(image: ImageOut) {
    setOpen(image);
    dialog.current?.showModal();
  }

  return (
    <div className={styles.gallery}>
      {canEdit && upload && (
        <div className={styles.roleRow}>
          <label>
            {t("images.role")}{" "}
            <select value={role} onChange={(e) => setRole(e.target.value as ImageRole)}>
              {IMAGE_ROLES.map((r) => (
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
      )}
      {canEdit && upload?.error && <Notice kind="error">{upload.error.message}</Notice>}
      {images.length === 0 ? (
        <p className="text-secondary">{canEdit ? t("images.emptyTextEdit") : t("images.emptyTextView")}</p>
      ) : (
        <ul className={styles.grid}>
          {images.map((image) => (
            <li key={image.id}>
              <button
                type="button"
                className={styles.thumbButton}
                onClick={() => show(image)}
                aria-label={image.quality_flags.length > 0 ? t("images.openWithWarnings") : t("images.open")}
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
                {image.quality_flags.length > 0 && (
                  <span className={styles.warningDot} aria-hidden="true">
                    !
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
      {canEdit && upload && <p className="text-secondary">{t("images.privacyNote")}</p>}

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
