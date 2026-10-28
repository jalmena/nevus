import { Camera, Image, TriangleAlert, Video } from "lucide-react";
import { useRef, useState, type RefObject } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Chip } from "@/design-system/components/Chip";
import { FileButton } from "@/design-system/components/FileButton";
import { Notice } from "@/design-system/components/Notice";
import { Row, RowList } from "@/design-system/components/Row";
import { Sheet, showDialog } from "@/design-system/components/Sheet";
import { LiveCamera, liveCameraAvailable } from "@/features/capture/LiveCamera";
import { Segmented } from "@/design-system/components/Segmented";
import {
  IMAGE_ROLES,
  imageUrl,
  markOf,
  normalisedOf,
  thumbOf,
  useDeleteImage,
  type ImageOut,
  type ImageRole,
  type RenditionKind,
} from "@/lib/images";
import styles from "./PhotoGallery.module.css";

interface Props {
  images: ImageOut[];
  canEdit: boolean;
  /** The previous visit's close-up: shown as "last time" and as the ghost in the live camera. */
  previousImageId?: string | null;
  upload?: {
    mutate: (input: { file: File; role: ImageRole }) => void;
    isPending: boolean;
    error: Error | null;
  };
  role: ImageRole;
  onRole: (role: ImageRole) => void;
  /** The hidden camera input the page's primary button clicks. */
  cameraRef: RefObject<HTMLInputElement | null>;
  addOpen: boolean;
  onAddOpen: (open: boolean) => void;
  quality: { flags: string[]; checking: boolean };
}

/** The photographs of a visit: one large, the others as a strip, and the ways to add one in a sheet. */
export function PhotoGallery({
  images,
  canEdit,
  upload,
  previousImageId,
  role,
  onRole,
  cameraRef,
  addOpen,
  onAddOpen,
  quality,
}: Props) {
  const { t, i18n } = useTranslation();
  const remove = useDeleteImage();
  const [current, setCurrent] = useState<string | null>(null);
  const [open, setOpen] = useState<ImageOut | null>(null);
  const [qualityOpen, setQualityOpen] = useState(false);
  const [view, setView] = useState<"mark" | "normalised" | "original">("mark");
  const [live, setLive] = useState(false);
  const preview = useRef<HTMLDialogElement>(null);
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, {
    dateStyle: "medium",
    timeStyle: "short",
  });
  const hero = images.find((image) => image.id === current) ?? images[0];
  const heroKind: RenditionKind =
    hero && markOf(hero) ? "mark" : hero && normalisedOf(hero) ? "normalised" : "preview";
  const firstFlag = quality.flags[0];

  function show(image: ImageOut) {
    setOpen(image);
    if (preview.current) showDialog(preview.current, true);
  }

  function closePreview() {
    if (preview.current) showDialog(preview.current, false);
  }

  function addFiles(files: File[]) {
    files.forEach((file) => upload?.mutate({ file, role }));
    onAddOpen(false);
  }

  const alt = (image: ImageOut) =>
    t("images.alt", {
      role: t(`images.roles.${image.role}`),
      date: image.captured_at ? dateFormat.format(new Date(image.captured_at)) : "",
    });

  return (
    <div className={styles.gallery}>
      {hero ? (
        <div className={styles.heroFrame}>
          <button
            type="button"
            className={styles.heroButton}
            onClick={() => show(hero)}
            aria-label={quality.flags.length > 0 ? t("images.openWithWarnings") : t("images.open")}
          >
            <img
              src={imageUrl(hero.id, heroKind)}
              alt={alt(hero)}
              width={hero.renditions.find((r) => r.kind === heroKind)?.width}
              height={hero.renditions.find((r) => r.kind === heroKind)?.height}
              className={styles.hero}
            />
          </button>
          {firstFlag ? (
            <Chip
              className={styles.qualityChip}
              icon={<TriangleAlert />}
              onClick={() => setQualityOpen(true)}
            >
              {t(`quality.flagsShort.${firstFlag}`, { defaultValue: firstFlag })}
            </Chip>
          ) : (
            quality.checking && (
              <span className={styles.checking} role="status">
                {t("quality.checking")}
              </span>
            )
          )}
        </div>
      ) : (
        <p className="text-secondary">{canEdit ? t("images.emptyTextEdit") : t("images.emptyTextView")}</p>
      )}
      {(images.length > 1 || (canEdit && upload && images.length > 0)) && (
        <ul className={styles.strip}>
          {images.map((image) => (
            <li key={image.id}>
              <button
                type="button"
                className={[styles.thumbButton, image.id === hero?.id ? styles.thumbCurrent : ""].join(" ")}
                onClick={() => setCurrent(image.id)}
                aria-label={alt(image)}
                aria-pressed={image.id === hero?.id}
              >
                <img src={thumbOf(image)} alt="" loading="lazy" className={styles.thumb} />
              </button>
            </li>
          ))}
          {canEdit && upload && (
            <li>
              <button
                type="button"
                className={styles.addTile}
                onClick={() => onAddOpen(true)}
                disabled={upload.isPending}
              >
                <Camera aria-hidden="true" />
                <span>{t("images.addPhoto")}</span>
              </button>
            </li>
          )}
        </ul>
      )}
      {canEdit && upload && images.length === 0 && previousImageId && (
        <div className={styles.lastTime}>
          <img src={imageUrl(previousImageId, "thumb")} alt={t("capture.lastTimeAlt")} />
          <span className="text-secondary">{t("capture.lastTime")}</span>
        </div>
      )}
      {canEdit && upload && images.length === 0 && (
        <div>
          <Button variant="quiet" onClick={() => onAddOpen(true)} disabled={upload.isPending}>
            {t("images.addPhoto")}
          </Button>
        </div>
      )}
      {canEdit && upload?.isPending && (
        <p className="text-secondary" role="status">
          {t("images.uploading")}
        </p>
      )}
      {canEdit && upload?.error && <Notice kind="error">{upload.error.message}</Notice>}

      {canEdit && upload && (
        <input
          ref={cameraRef}
          type="file"
          accept="image/*"
          capture="environment"
          className={styles.hiddenInput}
          aria-label={t("images.takePhoto")}
          onChange={(event) => {
            const files = Array.from(event.target.files ?? []);
            event.target.value = "";
            if (files.length > 0) addFiles(files);
          }}
        />
      )}

      {canEdit && upload && (
        <Sheet open={addOpen} title={t("images.addPhoto")} onClose={() => onAddOpen(false)}>
          <div className={styles.kinds} role="group" aria-label={t("images.kind")}>
            {IMAGE_ROLES.map((value) => (
              <Chip key={value} pressed={role === value} onClick={() => onRole(value)}>
                {t(`images.roles.${value}`)}
              </Chip>
            ))}
          </div>
          <RowList>
            <Row
              leading={<Camera />}
              title={t("images.takePhoto")}
              onClick={() => cameraRef.current?.click()}
            />
            {liveCameraAvailable() && (
              <Row
                leading={<Video />}
                title={t("capture.open")}
                onClick={() => {
                  onAddOpen(false);
                  setLive(true);
                }}
              />
            )}
            <li className={styles.fileRow}>
              <Image aria-hidden="true" />
              <FileButton label={t("images.chooseFile")} variant="secondary" multiple onFiles={addFiles} />
            </li>
          </RowList>
          <p className="text-secondary">{t("images.privacyNote")}</p>
        </Sheet>
      )}

      {live && upload && (
        <LiveCamera
          previousImageId={previousImageId}
          onCapture={(file) => upload.mutate({ file, role })}
          onClose={() => setLive(false)}
        />
      )}

      <Sheet open={qualityOpen} title={t("quality.title")} onClose={() => setQualityOpen(false)}>
        <ul className={styles.qualityList}>
          {quality.flags.map((flag) => (
            <li key={flag}>{t(`quality.flags.${flag}`, { defaultValue: flag })}</li>
          ))}
        </ul>
        <p className="text-secondary">{t("quality.hint")}</p>
      </Sheet>

      <dialog ref={preview} className={styles.preview} onClose={() => setOpen(null)}>
        {open && (
          <>
            <img src={imageUrl(open.id, lightboxKind(open, view))} alt={t(`images.roles.${open.role}`)} />
            {(markOf(open) || normalisedOf(open)) && (
              <div className={styles.previewView}>
                <Segmented
                  label={t("images.view")}
                  options={[
                    ...(markOf(open) ? [{ value: "mark" as const, label: t("images.markView") }] : []),
                    ...(normalisedOf(open)
                      ? [{ value: "normalised" as const, label: t("images.cardView") }]
                      : []),
                    { value: "original" as const, label: t("images.originalView") },
                  ]}
                  value={lightboxView(open, view)}
                  onChange={setView}
                />
              </div>
            )}
            <div className={styles.previewBar}>
              <span className="numeric">
                {open.captured_at ? dateFormat.format(new Date(open.captured_at)) : t("images.noDate")} ·{" "}
                {open.width}×{open.height}
              </span>
              <span className={styles.previewActions}>
                {canEdit && (
                  <Button
                    variant="quiet"
                    onClick={() => remove.mutate(open.id, { onSuccess: closePreview })}
                    disabled={remove.isPending}
                  >
                    {t("images.delete")}
                  </Button>
                )}
                <Button variant="secondary" onClick={closePreview}>
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

type LightboxView = "mark" | "normalised" | "original";

/** The view the lightbox can honour for this photo: a view it lacks falls back to the next one. */
function lightboxView(image: ImageOut, wanted: LightboxView): LightboxView {
  if (wanted === "mark" && !markOf(image)) return normalisedOf(image) ? "normalised" : "original";
  if (wanted === "normalised" && !normalisedOf(image)) return markOf(image) ? "mark" : "original";
  return wanted;
}

function lightboxKind(image: ImageOut, wanted: LightboxView): RenditionKind {
  const view = lightboxView(image, wanted);
  return view === "original" ? "preview" : view;
}
