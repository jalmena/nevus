import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { Select } from "@/design-system/components/Select";
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

/** The new mark, in a sheet over the map: a name, its type, when it was first noticed, how often to check. */
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
      <Select
        label={t("lesions.type")}
        value={type}
        onChange={(e) => setType(e.target.value as "mole" | "other")}
        options={[
          { value: "mole", label: t("lesions.types.mole") },
          { value: "other", label: t("lesions.types.other") },
        ]}
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
      {error && <Notice kind="error">{error}</Notice>}
      <div className={styles.actions}>
        <Button type="button" variant="quiet" onClick={onCancel}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" disabled={pending}>
          {t("lesions.create")}
        </Button>
      </div>
    </form>
  );
}
