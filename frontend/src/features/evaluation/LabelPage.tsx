import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { Segmented } from "@/design-system/components/Segmented";
import { PhotoCanvas, useCanvas } from "@/features/measure/PhotoCanvas";
import { useDeleteLabel, useEvaluationPhotos, useSaveLabel, type Outline } from "@/lib/evaluation";
import { imageUrl } from "@/lib/images";
import { useFit, type Point } from "@/lib/measurements";
import styles from "./evaluation.module.css";

type Tool = "tap" | "points";

/** The true outline of one photo, and whether the photo is good enough: the operator's label. */
export function LabelPage() {
  const { imageId = "" } = useParams();
  const { t } = useTranslation();
  const photos = useEvaluationPhotos("all");
  const photo = photos.data?.find((item) => item.image_id === imageId);
  const fit = useFit(imageId);
  const save = useSaveLabel(imageId);
  const remove = useDeleteLabel(imageId);
  const [draft, setDraft] = useState<Outline>([]);
  const [tool, setTool] = useState<Tool>("tap");
  const [quality, setQuality] = useState<"good" | "bad" | null>(null);

  useEffect(() => {
    if (photo?.label) {
      setDraft(photo.label.outline ?? []);
      setQuality(photo.label.quality ?? null);
    }
  }, [photo?.label]);

  if (photos.error) return <Notice kind="error">{photos.error.message}</Notice>;
  if (!photo) return <p className="text-secondary">…</p>;

  function onTap(point: Point) {
    if (tool === "points") {
      setDraft((current) => [...current, [Math.round(point.x * 10) / 10, Math.round(point.y * 10) / 10]]);
      return;
    }
    fit.mutate(
      { x: point.x, y: point.y, target: "lesion" },
      { onSuccess: (result) => result.outline && setDraft(result.outline) },
    );
  }

  return (
    <div className={styles.page}>
      <p>
        <Link to="/evaluation">{t("evaluation.backToList")}</Link>
      </p>
      <h1>{t("evaluation.labelTitle")}</h1>
      <p className="text-secondary">{t("evaluation.labelIntro")}</p>
      <Segmented
        label={t("evaluation.tool")}
        options={[
          { value: "tap", label: t("evaluation.tools.tap") },
          { value: "points", label: t("evaluation.tools.points") },
        ]}
        value={tool}
        onChange={setTool}
      />
      <PhotoCanvas
        src={imageUrl(photo.image_id, "full")}
        width={photo.upright_width}
        height={photo.upright_height}
        label={tool === "tap" ? t("evaluation.canvasTap") : t("evaluation.canvasPoints")}
        onTap={onTap}
      >
        {photo.proposal && <Polygon points={photo.proposal} kind="proposal" />}
        {draft.length > 0 && <Polygon points={draft} kind="label" closed={draft.length > 2} />}
      </PhotoCanvas>
      <p className="text-secondary">{t("evaluation.legend")}</p>
      <div className={styles.actions}>
        {photo.proposal && (
          <Button variant="secondary" onClick={() => setDraft(photo.proposal ?? [])}>
            {t("evaluation.fromProposal")}
          </Button>
        )}
        {tool === "points" && (
          <Button
            variant="secondary"
            onClick={() => setDraft((current) => current.slice(0, -1))}
            disabled={!draft.length}
          >
            {t("evaluation.undoPoint")}
          </Button>
        )}
        <Button variant="quiet" onClick={() => setDraft([])} disabled={!draft.length}>
          {t("evaluation.clear")}
        </Button>
      </div>
      {fit.error && <Notice kind="error">{fit.error.message}</Notice>}
      <fieldset className={styles.quality}>
        <legend>{t("evaluation.qualityQuestion")}</legend>
        {(["good", "bad"] as const).map((value) => (
          <label key={value}>
            <input
              type="radio"
              name="quality"
              checked={quality === value}
              onChange={() => setQuality(value)}
            />
            {t(`evaluation.qualityLabels.${value}`)}
          </label>
        ))}
      </fieldset>
      <div className={styles.actions}>
        <Button
          onClick={() => save.mutate({ outline: draft.length > 2 ? draft : null, quality })}
          disabled={save.isPending || (draft.length < 3 && quality === null)}
        >
          {t("evaluation.save")}
        </Button>
        {photo.label && (
          <Button variant="quiet" onClick={() => remove.mutate()} disabled={remove.isPending}>
            {t("evaluation.removeLabel")}
          </Button>
        )}
      </div>
      {save.isSuccess && <Notice kind="success">{t("evaluation.saved")}</Notice>}
      {(save.error ?? remove.error) && <Notice kind="error">{(save.error ?? remove.error)?.message}</Notice>}
    </div>
  );
}

function Polygon({
  points,
  kind,
  closed = true,
}: {
  points: Outline;
  kind: "proposal" | "label";
  closed?: boolean;
}) {
  const { unit } = useCanvas();
  const text = points.map((p) => p.join(",")).join(" ");
  const Shape = closed ? "polygon" : "polyline";
  return (
    <>
      <Shape points={text} className={styles.halo} strokeWidth={5 * unit} />
      <Shape
        points={text}
        className={kind === "proposal" ? styles.proposal : styles.label}
        strokeWidth={2 * unit}
      />
      {kind === "label" &&
        points.map(([x, y], index) => (
          <circle key={index} cx={x} cy={y} r={3 * unit} className={styles.vertex} />
        ))}
    </>
  );
}
