import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams, useSearchParams } from "react-router";
import { Notice } from "@/design-system/components/Notice";
import { Segmented } from "@/design-system/components/Segmented";
import { PhotoCanvas, WHOLE, useCanvas, type SharedView } from "@/features/measure/PhotoCanvas";
import { lesionTitle } from "@/features/lesions/lesionName";
import { scaleBarMm, useComparison, type Comparison } from "@/lib/comparisons";
import { imageUrl, type ImageOut } from "@/lib/images";
import { useLesion, useObservations, type ObservationOut } from "@/lib/lesions";
import styles from "./compare.module.css";

const MODES = ["side", "overlay", "wipe", "difference"] as const;
type Mode = (typeof MODES)[number];

interface Choice {
  image: ImageOut;
  visit: ObservationOut;
}

/** Photos with the reference card first (they align exactly), then close-ups. */
const ROLE_ORDER = ["with_reference", "close_up", "overview"];

function preferred(visit: ObservationOut | undefined): string {
  if (!visit) return "";
  const ranked = [...visit.images].sort(
    (x, y) => rank(x.role) - rank(y.role) || x.created_at.localeCompare(y.created_at),
  );
  return ranked[0]?.id ?? "";
}

function rank(role: string): number {
  const index = ROLE_ORDER.indexOf(role);
  return index === -1 ? ROLE_ORDER.length : index;
}

function upright(image: ImageOut): { width: number; height: number } {
  return image.orientation >= 5 && image.orientation <= 8
    ? { width: image.height, height: image.width }
    : { width: image.width, height: image.height };
}

/** Two photos of one mark: side by side with a shared zoom, or aligned on top of each other. */
export function ComparePage() {
  const { lesionId = "" } = useParams();
  const [search, setSearch] = useSearchParams();
  const { t, i18n } = useTranslation();
  const lesion = useLesion(lesionId);
  const observations = useObservations(lesionId);
  const [view, setView] = useState<SharedView>(WHOLE);
  const [opacity, setOpacity] = useState(50);
  const [split, setSplit] = useState(50);
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium" });

  const visits = [...(observations.data ?? [])]
    .filter((visit) => visit.images.length > 0)
    .sort((x, y) => x.captured_at.localeCompare(y.captured_at));
  const choices: Choice[] = visits.flatMap((visit) => visit.images.map((image) => ({ image, visit })));
  const a = search.get("a") ?? preferred(visits[0]);
  const b = search.get("b") ?? preferred(visits.at(-1));
  const requested = search.get("mode") as Mode | null;
  const comparison = useComparison(a, b);
  const aligned = comparison.data?.status === "aligned";
  const mode: Mode =
    requested && MODES.includes(requested) && (aligned || requested === "side") ? requested : "side";
  const first = choices.find((choice) => choice.image.id === a);
  const second = choices.find((choice) => choice.image.id === b);

  function choose(next: { a?: string; b?: string; mode?: Mode }) {
    const params = new URLSearchParams(search);
    for (const [key, value] of Object.entries(next)) if (value) params.set(key, value);
    setSearch(params, { replace: true });
    if (next.a || next.b) setView(WHOLE);
  }

  if (lesion.error) return <Notice kind="error">{lesion.error.message}</Notice>;
  if (!lesion.data || !observations.data) return <p className="text-secondary">…</p>;
  const back = (
    <p>
      <Link to={`/lesions/${lesionId}`}>{t("compare.back")}</Link>
    </p>
  );
  if (visits.length < 2 && choices.length < 2) {
    return (
      <div className={styles.page}>
        {back}
        <h1>{t("compare.title")}</h1>
        <Notice kind="info">{t("compare.needTwo")}</Notice>
      </div>
    );
  }

  const label = (choice: Choice) =>
    `${dateFormat.format(new Date(choice.visit.captured_at))} · ${t(`images.roles.${choice.image.role}`)}`;
  const picker = (side: "a" | "b", value: string) => (
    <label className={styles.picker}>
      <span className="text-secondary">{side === "a" ? t("compare.earlier") : t("compare.later")}</span>
      <select
        value={value}
        onChange={(event) => choose(side === "a" ? { a: event.target.value } : { b: event.target.value })}
      >
        {visits.map((visit) => (
          <optgroup key={visit.id} label={dateFormat.format(new Date(visit.captured_at))}>
            {visit.images.map((image) => (
              <option key={image.id} value={image.id}>
                {label({ image, visit })}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </label>
  );

  return (
    <div className={styles.page}>
      {back}
      <h1>{t("compare.titleFor", { name: lesionTitle(lesion.data, t) })}</h1>
      <div className={styles.pickers}>
        {picker("a", a)}
        {picker("b", b)}
      </div>
      {a === b && <Notice kind="info">{t("compare.samePhoto")}</Notice>}
      {comparison.isPending && a !== b && <p className="text-secondary">{t("compare.aligning")}</p>}
      {comparison.error && <Notice kind="error">{comparison.error.message}</Notice>}
      {comparison.data && <AlignmentNote comparison={comparison.data} />}
      {aligned && (
        <Segmented
          label={t("compare.mode")}
          options={MODES.map((value) => ({ value, label: t(`compare.modes.${value}`) }))}
          value={mode}
          onChange={(value) => choose({ mode: value })}
          wide
        />
      )}
      <p className="text-secondary">{t("compare.zoomHint")}</p>

      {mode === "side" && first && second && (
        <div className={styles.sideBySide}>
          {[first, second].map((choice, index) => {
            const size = upright(choice.image);
            const side = index === 0 ? comparison.data?.a : comparison.data?.b;
            return (
              <figure key={choice.image.id} className={styles.figure}>
                <PhotoCanvas
                  src={imageUrl(choice.image.id, "full")}
                  width={size.width}
                  height={size.height}
                  label={t("compare.canvas", { photo: label(choice) })}
                  view={view}
                  onViewChange={setView}
                >
                  {side?.mm_per_px ? <ScaleBar mmPerPx={side.mm_per_px} /> : null}
                </PhotoCanvas>
                <figcaption className="text-secondary">
                  {index === 0 ? t("compare.earlier") : t("compare.later")} · {label(choice)}
                </figcaption>
              </figure>
            );
          })}
        </div>
      )}

      {mode !== "side" && aligned && comparison.data && first && (
        <Layered
          comparison={comparison.data}
          base={first}
          mode={mode}
          opacity={opacity}
          split={split}
          view={view}
          onViewChange={setView}
          caption={`${label(first)} → ${second ? label(second) : ""}`}
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
    </div>
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
  base,
  mode,
  opacity,
  split,
  view,
  onViewChange,
  caption,
}: {
  comparison: Comparison;
  base: Choice;
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
        src={imageUrl(base.image.id, "full")}
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
