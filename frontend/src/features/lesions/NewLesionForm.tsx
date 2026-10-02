import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { TextField } from "@/design-system/components/TextField";
import type { MapPoint } from "@/features/bodymap/zones";
import { INTERVALS, type LesionIn } from "@/lib/lesions";
import { suggestName } from "@/lib/names";
import { zoneName } from "./lesionName";
import styles from "./lesions.module.css";

interface Props {
  point: MapPoint;
  view: string;
  pending: boolean;
  error?: string;
  onSubmit: (body: LesionIn) => void;
  onCancel: () => void;
}

export function NewLesionForm({ point, view, pending, error, onSubmit, onCancel }: Props) {
  const { t, i18n } = useTranslation();
  const [label, setLabel] = useState("");
  const [type, setType] = useState<"mole" | "other">("mole");
  const [firstNoticed, setFirstNoticed] = useState("");
  const [interval, setInterval] = useState<number>(90);

  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      type,
      status: "active",
      label: label.trim() || null,
      location: { zone: point.zone, x: point.x, y: point.y },
      first_noticed_on: firstNoticed || null,
      interval_days: interval,
    });
  }

  return (
    <form className={styles.form} onSubmit={submit}>
      <h3>{t("lesions.newTitle")}</h3>
      <p className="text-secondary">
        {t("bodymap.selected", { zone: zoneName(point.zone, t), view: t(`bodymap.views.${view}`) })}
      </p>
      <TextField
        label={t("lesions.label")}
        hint={t("lesions.labelHint")}
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        maxLength={120}
      />
      <div>
        <Button
          type="button"
          variant="quiet"
          onClick={() => setLabel(suggestName(i18n.resolvedLanguage ?? "en"))}
        >
          {t("lesions.suggestName")}
        </Button>
      </div>
      <label className={styles.row}>
        <span>{t("lesions.type")}</span>
        <select value={type} onChange={(e) => setType(e.target.value as "mole" | "other")}>
          <option value="mole">{t("lesions.types.mole")}</option>
          <option value="other">{t("lesions.types.other")}</option>
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
      {error && <Notice kind="error">{error}</Notice>}
      <div className={styles.actions}>
        <Button type="submit" disabled={pending}>
          {t("lesions.create")}
        </Button>
        <Button type="button" variant="quiet" onClick={onCancel}>
          {t("common.cancel")}
        </Button>
      </div>
    </form>
  );
}
