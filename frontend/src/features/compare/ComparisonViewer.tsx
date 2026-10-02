import { useEffect, useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { Notice } from "@/design-system/components/Notice";
import { Segmented } from "@/design-system/components/Segmented";
import { PhotoCanvas, WHOLE, useCanvas, type SharedView } from "@/features/measure/PhotoCanvas";
import { scaleBarMm, useComparison, type Comparison } from "@/lib/comparisons";
import { imageUrl } from "@/lib/images";
import styles from "./compare.module.css";

export const MODES = ["side", "overlay", "wipe", "difference"] as const;
export type Mode = (typeof MODES)[number];

/** One photo to compare: its id, its upright size and how to name it. */
export interface ComparedPhoto {
  id: string;
  width: number;
  height: number;
  label: string;
}

/**
 * Two photos, earlier (a) and later (b): side by side with one zoom, or lined up on top of each other
 * when the alignment trusts itself. The mode can be held by the page (in its address) or here.
 */
export function ComparisonViewer({
  a,
  b,
  mode: wanted,
  onMode,
}: {
  a: ComparedPhoto;
  b: ComparedPhoto;
  mode?: Mode | null;
  onMode?: (mode: Mode) => void;
}) {
  const { t } = useTranslation();
  const comparison = useComparison(a.id, b.id);
  const [view, setView] = useState<SharedView>(WHOLE);
  const [opacity, setOpacity] = useState(50);
  const [split, setSplit] = useState(50);
  const [own, setOwn] = useState<Mode>("side");
  const aligned = comparison.data?.status === "aligned";
  const requested = wanted ?? own;
  const mode: Mode = MODES.includes(requested) && (aligned || requested === "side") ? requested : "side";

  useEffect(() => setView(WHOLE), [a.id, b.id]);

  function choose(next: Mode) {
    if (onMode) onMode(next);
    else setOwn(next);
  }

  return (
    <>
      {a.id === b.id && <Notice kind="info">{t("compare.samePhoto")}</Notice>}
      {comparison.isPending && a.id !== b.id && <p className="text-secondary">{t("compare.aligning")}</p>}
      {comparison.error && <Notice kind="error">{comparison.error.message}</Notice>}
      {comparison.data && <AlignmentNote comparison={comparison.data} />}
      {aligned && (
        <Segmented
          label={t("compare.mode")}
          options={MODES.map((value) => ({ value, label: t(`compare.modes.${value}`) }))}
          value={mode}
          onChange={choose}
          wide
        />
      )}
      <p className="text-secondary">{t("compare.zoomHint")}</p>

      {mode === "side" && (
        <div className={styles.sideBySide}>
          {[a, b].map((photo, index) => {
            const side = index === 0 ? comparison.data?.a : comparison.data?.b;
            return (
              <figure key={photo.id} className={styles.figure}>
                <PhotoCanvas
                  src={imageUrl(photo.id, "full")}
                  width={photo.width}
                  height={photo.height}
                  label={t("compare.canvas", { photo: photo.label })}
                  view={view}
                  onViewChange={setView}
                >
                  {side?.mm_per_px ? <ScaleBar mmPerPx={side.mm_per_px} /> : null}
                </PhotoCanvas>
                <figcaption className="text-secondary">
                  {index === 0 ? t("compare.earlier") : t("compare.later")} · {photo.label}
                </figcaption>
              </figure>
            );
          })}
        </div>
      )}

      {mode !== "side" && aligned && comparison.data && (
        <Layered
          comparison={comparison.data}
          baseId={a.id}
          mode={mode}
          opacity={opacity}
          split={split}
          view={view}
          onViewChange={setView}
          caption={`${a.label} → ${b.label}`}
        />
      )}
      {mode === "overlay" && (
        <label className={styles.slider}>
          <span>{t("compare.opacity")}</span>
          <input
            type="range"
            min={0}
            max={100}
            value={opacity}
            onChange={(event) => setOpacity(Number(event.target.value))}
            aria-valuetext={`${opacity}%`}
          />
        </label>
      )}
      {mode === "wipe" && (
        <label className={styles.slider}>
          <span>{t("compare.wipe")}</span>
          <input
            type="range"
            min={0}
            max={100}
            value={split}
            onChange={(event) => setSplit(Number(event.target.value))}
            aria-valuetext={`${split}%`}
          />
        </label>
      )}
      {mode === "difference" && <DifferenceLegend />}
    </>
  );
}

function AlignmentNote({ comparison }: { comparison: Comparison }) {
  const { t } = useTranslation();
  if (comparison.status === "aligned") {
    return (
      <p className="text-secondary">
        {comparison.method === "card"
          ? t("compare.alignedCard")
          : t("compare.alignedPoints", { count: comparison.inliers ?? 0 })}
      </p>
    );
  }
  return (
    <Notice kind="info">
      {t("compare.abstained")} {comparison.reason ? t(`compare.reasons.${comparison.reason}`) : ""}{" "}
      {t("compare.abstainedHint")}
    </Notice>
  );
}

function Layered({
  comparison,
  baseId,
  mode,
  opacity,
  split,
  view,
  onViewChange,
  caption,
}: {
  comparison: Comparison;
  baseId: string;
  mode: Exclude<Mode, "side">;
  opacity: number;
  split: number;
  view: SharedView;
  onViewChange: (view: SharedView) => void;
  caption: string;
}) {
  const { t } = useTranslation();
  const { upright_width: width, upright_height: height } = comparison.a;
  return (
    <figure className={styles.figure}>
      <PhotoCanvas
        src={imageUrl(baseId, "full")}
        width={width}
        height={height}
        label={t("compare.canvasLayered", { mode: t(`compare.modes.${mode}`) })}
        view={view}
        onViewChange={onViewChange}
      >
        {mode === "overlay" && comparison.overlay_url && (
          <image
            href={comparison.overlay_url}
            width={width}
            height={height}
            preserveAspectRatio="none"
            opacity={opacity / 100}
          />
        )}
        {mode === "wipe" && comparison.overlay_url && (
          <Wipe href={comparison.overlay_url} width={width} height={height} split={split} />
        )}
        {mode === "difference" && comparison.heatmap_url && (
          <image href={comparison.heatmap_url} width={width} height={height} preserveAspectRatio="none" />
        )}
        {comparison.a.mm_per_px ? <ScaleBar mmPerPx={comparison.a.mm_per_px} /> : null}
      </PhotoCanvas>
      <figcaption className="text-secondary">{caption}</figcaption>
    </figure>
  );
}

function Wipe({
  href,
  width,
  height,
  split,
}: {
  href: string;
  width: number;
  height: number;
  split: number;
}) {
  const { unit } = useCanvas();
  const clip = useId();
  const x = (split / 100) * width;
  return (
    <>
      <defs>
        <clipPath id={clip}>
          <rect x={x} y={0} width={width - x} height={height} />
        </clipPath>
      </defs>
      <image
        href={href}
        width={width}
        height={height}
        preserveAspectRatio="none"
        clipPath={`url(#${clip})`}
      />
      <line className={styles.split} x1={x} y1={0} x2={x} y2={height} strokeWidth={2 * unit} />
    </>
  );
}

/** A round length at the bottom left of what is visible, redrawn as the zoom changes. Approximate by nature. */
function ScaleBar({ mmPerPx }: { mmPerPx: number }) {
  const { unit, view } = useCanvas();
  const { i18n } = useTranslation();
  const mm = scaleBarMm(mmPerPx * unit);
  const length = mm / mmPerPx;
  const x = view.x + 16 * unit;
  const y = view.y + view.h - 18 * unit;
  const number = new Intl.NumberFormat(i18n.resolvedLanguage, { maximumFractionDigits: 1 }).format(mm);
  return (
    <g className={styles.scaleBar} aria-hidden="true">
      <line className={styles.scaleHalo} x1={x} y1={y} x2={x + length} y2={y} strokeWidth={7 * unit} />
      <line x1={x} y1={y} x2={x + length} y2={y} strokeWidth={3 * unit} />
      <text x={x} y={y - 12 * unit} fontSize={13 * unit} strokeWidth={4 * unit}>
        {number} mm
      </text>
    </g>
  );
}

function DifferenceLegend() {
  const { t } = useTranslation();
  return (
    <div className={styles.legend}>
      <div className={styles.ramp} aria-hidden="true" />
      <div className={styles.rampLabels} aria-hidden="true">
        <span>{t("compare.similar")}</span>
        <span>{t("compare.different")}</span>
      </div>
      <p className="text-secondary">{t("compare.differenceNote")}</p>
    </div>
  );
}
