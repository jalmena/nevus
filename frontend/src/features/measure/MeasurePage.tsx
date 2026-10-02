import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { TextField } from "@/design-system/components/TextField";
import { useSession } from "@/lib/auth/session";
import { imageUrl } from "@/lib/images";
import { useObservation } from "@/lib/lesions";
import {
  COINS,
  formatMm,
  previewMeasurement,
  useAddScaleReference,
  useCreateMeasurement,
  useFit,
  useImageScale,
  type Circle,
  type Denomination,
  type MeasurementIn,
  type MeasurementPreview,
  type Point,
} from "@/lib/measurements";
import { Handle, PhotoCanvas, useCanvas } from "./PhotoCanvas";
import styles from "./measure.module.css";

type Shape = { type: "outline"; points: number[][] } | ({ type: "circle" } & Circle);

export function MeasurePage() {
  const { observationId = "", imageId = "" } = useParams();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const session = useSession();
  const observation = useObservation(observationId);
  const scale = useImageScale(imageId);
  const fit = useFit(imageId);
  const addReference = useAddScaleReference(imageId);
  const create = useCreateMeasurement(observationId);
  const showUncertainty = session.data?.user.show_uncertainty ?? true;

  const [step, setStep] = useState<"scale" | "mark">("scale");
  const [referenceId, setReferenceId] = useState<string | null>(null);
  const [tool, setTool] = useState<"none" | "coin" | "manual">("none");
  const [coin, setCoin] = useState<Circle | null>(null);
  const [denomination, setDenomination] = useState<Denomination>("1e");
  const [line, setLine] = useState<Point[]>([]);
  const [lengthMm, setLengthMm] = useState("10");
  const [shape, setShape] = useState<Shape | null>(null);
  const [fitted, setFitted] = useState<Circle | null>(null);
  const [method, setMethod] = useState<"assisted" | "manual">("assisted");
  const [preview, setPreview] = useState<MeasurementPreview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const data = scale.data;
  const width = data?.upright_width ?? 1;
  const height = data?.upright_height ?? 1;
  const cardReference = data?.references.find((r) => r.kind === "card");

  useEffect(() => {
    if (!referenceId && cardReference) setReferenceId(cardReference.id);
  }, [cardReference, referenceId]);

  useEffect(() => {
    if (!shape || !referenceId) {
      setPreview(null);
      return;
    }
    const body: MeasurementIn = { image_id: imageId, scale_reference_id: referenceId, method, shape };
    const timer = window.setTimeout(() => {
      previewMeasurement(observationId, body)
        .then((value) => {
          setPreview(value);
          setPreviewError(null);
        })
        .catch((error: Error) => setPreviewError(error.message));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [shape, referenceId, method, imageId, observationId]);

  function onTap(point: Point) {
    if (step === "scale" && tool === "coin") {
      fit.mutate(
        { x: point.x, y: point.y, target: "coin" },
        {
          onSuccess: (result) => setCoin({ cx: result.cx, cy: result.cy, r: result.r }),
          onError: () => setCoin({ cx: point.x, cy: point.y, r: width * 0.05 }),
        },
      );
    } else if (step === "scale" && tool === "manual") {
      setLine((current) => (current.length >= 2 ? current : [...current, point]));
    } else if (step === "mark") {
      fit.mutate(
        { x: point.x, y: point.y, target: "lesion" },
        {
          onSuccess: (result) => {
            setFitted({ cx: result.cx, cy: result.cy, r: result.r });
            setMethod("assisted");
            setShape(
              result.outline
                ? { type: "outline", points: result.outline }
                : { type: "circle", cx: result.cx, cy: result.cy, r: result.r },
            );
          },
          onError: () => {
            setMethod("manual");
            setShape({ type: "circle", cx: point.x, cy: point.y, r: width * 0.03 });
          },
        },
      );
    }
  }

  function confirmCoin() {
    if (!coin) return;
    addReference.mutate(
      { kind: "coin", ...coin, denomination },
      {
        onSuccess: (reference) => {
          setReferenceId(reference.id);
          setTool("none");
          setStep("mark");
        },
      },
    );
  }

  function confirmLine() {
    const [a, b] = line;
    const length = Number(lengthMm.replace(",", "."));
    if (!a || !b || !(length > 0)) return;
    addReference.mutate(
      { kind: "manual", x1: a.x, y1: a.y, x2: b.x, y2: b.y, length_mm: length },
      {
        onSuccess: (reference) => {
          setReferenceId(reference.id);
          setTool("none");
          setStep("mark");
        },
      },
    );
  }

  function asCircle() {
    const base = fitted ?? (shape?.type === "circle" ? shape : null);
    if (base) {
      setShape({ type: "circle", ...base });
      setMethod("manual");
    }
  }

  function save() {
    if (!shape || !referenceId) return;
    create.mutate(
      { image_id: imageId, scale_reference_id: referenceId, method, shape },
      { onSuccess: () => void navigate(`/observations/${observationId}`) },
    );
  }

  if (scale.error) return <Notice kind="error">{scale.error.message}</Notice>;
  if (!data || !observation.data) return <p className="text-secondary">…</p>;
  const locale = i18n.resolvedLanguage ?? "en";

  return (
    <div className={styles.page}>
      <p>
        <Link to={`/observations/${observationId}`}>{t("measure.back")}</Link>
      </p>
      <h1>{t("measure.title")}</h1>
      <ol className={styles.steps} aria-label={t("measure.stepsLabel")}>
        <li aria-current={step === "scale" ? "step" : undefined}>{t("measure.stepScale")}</li>
        <li aria-current={step === "mark" ? "step" : undefined}>{t("measure.stepMark")}</li>
      </ol>

      <PhotoCanvas
        src={imageUrl(imageId, "full")}
        width={width}
        height={height}
        label={step === "scale" ? t("measure.canvasScale") : t("measure.canvasMark")}
        onTap={onTap}
      >
        {data.card?.found && data.card.centre_px && (
          <CardMarker x={data.card.centre_px[0] ?? 0} y={data.card.centre_px[1] ?? 0} />
        )}
        {step === "scale" && tool === "coin" && coin && (
          <CircleEditor circle={coin} onChange={setCoin} label={t("measure.coin")} />
        )}
        {step === "scale" && tool === "manual" && <LineEditor points={line} onChange={setLine} />}
        {step === "mark" && shape?.type === "outline" && <OutlineView points={shape.points} />}
        {step === "mark" && shape?.type === "circle" && (
          <CircleEditor
            circle={shape}
            onChange={(next) => {
              setMethod("manual");
              setShape({ type: "circle", ...next });
            }}
            label={t("measure.mark")}
          />
        )}
      </PhotoCanvas>
      <p className="text-secondary">{t("measure.zoomHint")}</p>

      {step === "scale" && (
        <section className={styles.panel} aria-labelledby="scale-heading">
          <h2 id="scale-heading">{t("measure.stepScale")}</h2>
          {!data.card_checked && <p role="status">{t("measure.cardSearching")}</p>}
          {data.card?.found && (
            <Notice kind={(data.card.flags ?? []).includes("tilted") ? "attention" : "success"}>
              {(data.card.flags ?? []).includes("tilted")
                ? t("measure.cardTilted", {
                    tilt: Math.round(data.card.tilt_deg ?? 0),
                    limit: data.tilt_limit_deg,
                  })
                : t("measure.cardFound", { tilt: Math.round(data.card.tilt_deg ?? 0) })}
              {(data.card.flags ?? []).includes("card_small") && <> {t("measure.cardSmall")}</>}
            </Notice>
          )}
          {data.card_checked && !data.card?.found && <p>{t("measure.cardNotFound")}</p>}

          <div className={styles.actions}>
            {cardReference && (
              <Button
                onClick={() => {
                  setReferenceId(cardReference.id);
                  setStep("mark");
                }}
              >
                {t("measure.useCard")}
              </Button>
            )}
            <Button variant={tool === "coin" ? "primary" : "secondary"} onClick={() => setTool("coin")}>
              {t("measure.withCoin")}
            </Button>
            <Button variant={tool === "manual" ? "primary" : "secondary"} onClick={() => setTool("manual")}>
              {t("measure.withLine")}
            </Button>
          </div>

          {tool === "coin" && (
            <div className={styles.tool}>
              <p>{coin ? t("measure.coinAdjust") : t("measure.coinTap")}</p>
              <label className={styles.row}>
                <span>{t("measure.denomination")}</span>
                <select
                  value={denomination}
                  onChange={(e) => setDenomination(e.target.value as Denomination)}
                >
                  {COINS.map((c) => (
                    <option key={c.id} value={c.id}>
                      {t(`measure.coins.${c.id}`)} ({new Intl.NumberFormat(locale).format(c.mm)} mm)
                    </option>
                  ))}
                </select>
              </label>
              <p className="text-secondary">{t("measure.coinTiltNote")}</p>
              <Button onClick={confirmCoin} disabled={!coin || addReference.isPending}>
                {t("measure.useThisCoin")}
              </Button>
            </div>
          )}
          {tool === "manual" && (
            <div className={styles.tool}>
              <p>
                {line.length < 2 ? t("measure.lineTap", { count: 2 - line.length }) : t("measure.lineAdjust")}
              </p>
              <TextField
                label={t("measure.lengthMm")}
                inputMode="decimal"
                value={lengthMm}
                onChange={(e) => setLengthMm(e.target.value)}
              />
              <div className={styles.actions}>
                <Button onClick={confirmLine} disabled={line.length < 2 || addReference.isPending}>
                  {t("measure.useThisLine")}
                </Button>
                <Button variant="quiet" onClick={() => setLine([])}>
                  {t("measure.clearLine")}
                </Button>
              </div>
            </div>
          )}
          {addReference.error && <Notice kind="error">{addReference.error.message}</Notice>}
        </section>
      )}

      {step === "mark" && (
        <section className={styles.panel} aria-labelledby="mark-heading">
          <h2 id="mark-heading">{t("measure.stepMark")}</h2>
          <p>{shape ? t("measure.markAdjust") : t("measure.markTap")}</p>
          {fit.isPending && <p role="status">{t("common.working")}</p>}
          {preview && (
            <dl className={styles.result} aria-live="polite">
              <div>
                <dt>{t("measure.longest")}</dt>
                <dd className="numeric">
                  {formatMm(preview.longest_mm, preview.sigma_longest_mm, locale, showUncertainty)}
                </dd>
              </div>
              <div>
                <dt>{t("measure.across")}</dt>
                <dd className="numeric">
                  {formatMm(
                    preview.perpendicular_mm,
                    preview.sigma_perpendicular_mm,
                    locale,
                    showUncertainty,
                  )}
                </dd>
              </div>
              <div>
                <dt>{t("measure.area")}</dt>
                <dd className="numeric">
                  {new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(preview.area_mm2)} mm²
                </dd>
              </div>
            </dl>
          )}
          {preview?.flags.map((flag) => (
            <Notice key={flag} kind="attention">
              {t(`measure.flags.${flag}`, { limit: data.tilt_limit_deg })}
            </Notice>
          ))}
          {previewError && <Notice kind="error">{previewError}</Notice>}
          <div className={styles.actions}>
            <Button onClick={save} disabled={!shape || !referenceId || create.isPending}>
              {t("measure.save")}
            </Button>
            {shape?.type === "outline" && (
              <Button variant="secondary" onClick={asCircle}>
                {t("measure.asCircle")}
              </Button>
            )}
            <Button variant="quiet" onClick={() => setShape(null)} disabled={!shape}>
              {t("measure.again")}
            </Button>
            <Button variant="quiet" onClick={() => setStep("scale")}>
              {t("measure.changeScale")}
            </Button>
          </div>
          {create.error && <Notice kind="error">{create.error.message}</Notice>}
          <p className="text-secondary">{t("measure.disclaimer")}</p>
        </section>
      )}
    </div>
  );
}

function CardMarker({ x, y }: { x: number; y: number }) {
  const { unit } = useCanvas();
  const s = 14 * unit;
  return (
    <g className={styles.card} strokeWidth={2 * unit} aria-hidden="true">
      <line x1={x - s} y1={y} x2={x + s} y2={y} />
      <line x1={x} y1={y - s} x2={x} y2={y + s} />
    </g>
  );
}

function CircleEditor({
  circle,
  onChange,
  label,
}: {
  circle: Circle;
  onChange: (c: Circle) => void;
  label: string;
}) {
  const { t } = useTranslation();
  const { unit } = useCanvas();
  return (
    <g>
      <circle className={styles.shape} cx={circle.cx} cy={circle.cy} r={circle.r} strokeWidth={2 * unit} />
      <Handle
        x={circle.cx}
        y={circle.cy}
        label={t("measure.moveHandle", { what: label })}
        onMove={(p) => onChange({ ...circle, cx: p.x, cy: p.y })}
      />
      <Handle
        x={circle.cx + circle.r}
        y={circle.cy}
        label={t("measure.sizeHandle", { what: label })}
        onMove={(p) => onChange({ ...circle, r: Math.max(2, Math.hypot(p.x - circle.cx, p.y - circle.cy)) })}
      />
    </g>
  );
}

function LineEditor({ points, onChange }: { points: Point[]; onChange: (p: Point[]) => void }) {
  const { t } = useTranslation();
  const { unit } = useCanvas();
  const [a, b] = points;
  return (
    <g>
      {a && b && <line className={styles.shape} x1={a.x} y1={a.y} x2={b.x} y2={b.y} strokeWidth={2 * unit} />}
      {points.map((point, index) => (
        <Handle
          key={index}
          x={point.x}
          y={point.y}
          label={t("measure.lineEnd", { n: index + 1 })}
          onMove={(next) => onChange(points.map((p, i) => (i === index ? next : p)))}
        />
      ))}
    </g>
  );
}

function OutlineView({ points }: { points: number[][] }) {
  const { unit } = useCanvas();
  return (
    <polygon
      className={styles.shape}
      points={points.map(([x, y]) => `${x},${y}`).join(" ")}
      strokeWidth={2 * unit}
      aria-hidden="true"
    />
  );
}
