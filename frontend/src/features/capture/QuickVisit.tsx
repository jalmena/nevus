import { useState, type ChangeEvent, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { useSession } from "@/lib/auth/session";
import { IMAGE_ROLES, type ImageRole } from "@/lib/images";
import { queueVisit } from "@/lib/offline/outbox";
import styles from "./capture.module.css";

/** A visit recorded without a connection: photos and a note, kept on this device until it can upload. */
export function QuickVisit({
  lesionId,
  lesionLabel,
  onDone,
}: {
  lesionId: string;
  lesionLabel: string;
  onDone: () => void;
}) {
  const { t } = useTranslation();
  const session = useSession();
  const [photos, setPhotos] = useState<{ file: File; role: ImageRole }[]>([]);
  const [role, setRole] = useState<ImageRole>("close_up");
  const [notes, setNotes] = useState("");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const userId = session.data?.user.id;

  function onFile(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    setPhotos((current) => [...current, ...files.map((file) => ({ file, role }))]);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!userId) return;
    try {
      await queueVisit({
        userId,
        lesionId,
        lesionLabel,
        notes: notes.trim() || null,
        photos: photos.map((p) => ({ file: p.file, role: p.role, name: p.file.name || "photo.jpg" })),
      });
      setSaved(true);
      onDone();
    } catch (failure) {
      setError((failure as Error).message);
    }
  }

  if (saved) return <Notice kind="success">{t("offline.saved")}</Notice>;
  return (
    <form className={styles.quick} onSubmit={(e) => void save(e)}>
      <Notice kind="info">{t("offline.quickIntro")}</Notice>
      <label className={styles.row}>
        <span>{t("images.role")}</span>
        <select value={role} onChange={(e) => setRole(e.target.value as ImageRole)}>
          {IMAGE_ROLES.map((r) => (
            <option key={r} value={r}>
              {t(`images.roles.${r}`)}
            </option>
          ))}
        </select>
      </label>
      <Button className={styles.fileButton} type="button">
        {t("images.takePhoto")}
        <input
          type="file"
          accept="image/*"
          capture="environment"
          onChange={onFile}
          aria-label={t("images.takePhoto")}
        />
      </Button>
      {photos.length > 0 && <p>{t("offline.photosReady", { count: photos.length })}</p>}
      <label>
        <span className="text-secondary">{t("observations.notes")}</span>
        <textarea
          className={styles.textarea}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          maxLength={4000}
        />
      </label>
      {error && <Notice kind="error">{error}</Notice>}
      <Button type="submit" disabled={photos.length === 0 && !notes.trim()}>
        {t("offline.keep")}
      </Button>
    </form>
  );
}
