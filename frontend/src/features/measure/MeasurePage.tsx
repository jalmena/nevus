import { Check, Circle, RotateCcw, Scaling } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams, useSearchParams } from "react-router";
import { Button } from "@/design-system/components/Button";
import { IconButton } from "@/design-system/components/IconButton";
import { Notice } from "@/design-system/components/Notice";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Select } from "@/design-system/components/Select";
import { TextField } from "@/design-system/components/TextField";
import { shortDate } from "@/lib/dates";
import { useSession } from "@/lib/auth/session";
import { imageUrl } from "@/lib/images";
import { personRail } from "@/features/persons/personRail";
import { useLesion, useObservation } from "@/lib/lesions";
import { usePerson } from "@/lib/persons";
import {
  COINS,
  formatMm,
  previewMeasurement,
  useAddScaleReference,
  useCreateMeasurement,
  useFit,
  useImageScale,
  type Circle as CircleShape,
  type Denomination,
  type MeasurementIn,
  type MeasurementPreview,
  type Point,
} from "@/lib/measurements";
import { useProposals } from "@/lib/proposals";
import { Handle, PhotoCanvas, useCanvas } from "./PhotoCanvas";
import styles from "./measure.module.css";

type Shape = { type: "outline"; points: number[][] } | ({ type: "circle" } & CircleShape);

/** Measuring a mark on one photo: first the scale (the card, a coin or a known length), then the mark. */
export function MeasurePage() {
  const { observationId = "", imageId = "" } = useParams();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const session = useSession();
  const observation = useObservation(observationId);
  const lesion = useLesion(observation.data?.lesion_id ?? "");
  const person = usePerson(lesion.data?.person_id ?? "");
  const scale = useImageScale(imageId);
  const fit = useFit(imageId);
  const addReference = useAddScaleReference(imageId);
  const create = useCreateMeasurement(observationId);
  const showUncertainty = session.data?.user.show_uncertainty ?? true;

  const [step, setStep] = useState<"scale" | "mark">("scale");
  const [referenceId, setReferenceId] = useState<string | null>(null);
  const [tool, setTool] = useState<"none" | "coin" | "manual">("none");
  const [coin, setCoin] = useState<CircleShape | null>(null);
  const [denomination, setDenomination] = useState<Denomination>("1e");
  const [line, setLine] = useState<Point[]>([]);
  const [lengthMm, setLengthMm] = useState("10");
  const [shape, setShape] = useState<Shape | null>(null);
  const [fitted, setFitted] = useState<CircleShape | null>(null);
  const [method, setMethod] = useState<"assisted" | "manual">("assisted");
  const [preview, setPreview] = useState<MeasurementPreview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [search] = useSearchParams();
  const proposals = useProposals(search.get("proposal") ? imageId : "");
  const proposed = proposals.data?.find((item) => item.id === search.get("proposal"))?.outline ?? null;

  const data = scale.data;
  const width = data?.upright_width ?? 1;
  const height = data?.upright_height ?? 1;
  const cardReference = data?.references.find((r) => r.kind === "card");

  useEffect(() => {
    if (!referenceId && cardReference) setReferenceId(cardReference.id);
  }, [cardReference, referenceId]);

  // Adjusting an experimental proposal: its outline is where the mark step starts.
  useEffect(() => {
    if (step === "mark" && !shape && proposed) setShape({ type: "outline", points: proposed });
  }, [step, shape, proposed]);

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
  const cardFound = Boolean(data.card?.found);
  const tilted = (data.card?.flags ?? []).includes("tilted");

  const primary =
    step === "mark"
      ? {
          label: t("measure.save"),
          disabled: !shape || !referenceId,
          pending: create.isPending,
          onClick: save,
        }
      : tool === "coin"
        ? {
            label: t("measure.useThisCoin"),
            disabled: !coin,
            pending: addReference.isPending,
            onClick: confirmCoin,
          }
        : tool === "manual"
          ? {
              label: t("measure.useThisLine"),
              disabled: line.length < 2,
              pending: addReference.isPending,
              onClick: confirmLine,
            }
          : cardReference
            ? {
                label: t("measure.useCard"),
                onClick: () => {
                  setReferenceId(cardReference.id);
                  setStep("mark");
                },
              }
            : data.card_checked
              ? { label: t("measure.withCoin"), onClick: () => setTool("coin") }
              : undefined;
  const secondary =
    step === "scale" && tool !== "none"
      ? { label: t("common.cancel"), onClick: () => setTool("none") }
      : undefined;

  return (
    <div className={[styles.page, "page-wide"].join(" ")}>
      <PageHeader
        back={{
          to: `/observations/${observationId}`,
          label: shortDate(locale, observation.data.captured_at),
        }}
        title={t("measure.title")}
        meta={[
          <span
            key="scale"
            className={step === "scale" ? styles.stepCurrent : styles.step}
            aria-current={step === "scale" ? "step" : undefined}
          >
            {t("measure.stepper", { n: 1, name: t("measure.stepScale") })}
          </span>,
          <span
            key="mark"
            className={step === "mark" ? styles.stepCurrent : styles.step}
            aria-current={step === "mark" ? "step" : undefined}
          >
            {t("measure.stepper", { n: 2, name: t("measure.stepMark") })}
          </span>,
        ]}
        help={{ title: t("common.help"), content: <p>{t("measure.zoomHint")}</p> }}
        primary={primary}
        secondary={secondary}
        instruction={
          step === "scale" && tool === "none" && !data.card_checked ? t("measure.cardSearching") : undefined
        }
        rail={lesion.data ? personRail(t, lesion.data.person_id, person.data?.display_name) : undefined}
      />

      <div className={styles.layout}>
        <div className={styles.canvasFrame}>
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
        </div>

        <div className={styles.panel}>
          {step === "scale" && (
            <>
              {!data.card_checked && (
                <p className="text-secondary" role="status">
                  {t("measure.cardSearching")}
                </p>
              )}
              {cardFound && (
                <p className={[styles.status, tilted ? styles.statusAttention : styles.statusOk].join(" ")}>
                  <Check aria-hidden="true" />
                  <span>
                    {tilted
                      ? t("measure.cardTilted", {
                          tilt: Math.round(data.card?.tilt_deg ?? 0),
                          limit: data.tilt_limit_deg,
                        })
                      : t("measure.cardFound", { tilt: Math.round(data.card?.tilt_deg ?? 0) })}
                    {(data.card?.flags ?? []).includes("card_small") && <> {t("measure.cardSmall")}</>}
                  </span>
                </p>
              )}
              {data.card_checked && !cardFound && (
                <p className="text-secondary">{t("measure.cardNotFound")}</p>
              )}
              {tool === "none" && data.card_checked && (
                <div className={styles.alternatives}>
                  {cardReference && (
                    <Button variant="secondary" onClick={() => setTool("coin")}>
                      {t("measure.withCoin")}
                    </Button>
                  )}
                  <Button variant="secondary" onClick={() => setTool("manual")}>
                    {t("measure.withLine")}
                  </Button>
                </div>
              )}
              {tool === "coin" && (
                <div className={styles.tool}>
                  <p>{coin ? t("measure.coinAdjust") : t("measure.coinTap")}</p>
                  <Select
                    label={t("measure.denomination")}
                    value={denomination}
                    onChange={(e) => setDenomination(e.target.value as Denomination)}
                    options={COINS.map((c) => ({
                      value: c.id,
                      label: `${t(`measure.coins.${c.id}`)} (${new Intl.NumberFormat(locale).format(c.mm)} mm)`,
                    }))}
                  />
                  <p className="text-secondary">{t("measure.coinTiltNote")}</p>
                </div>
              )}
              {tool === "manual" && (
                <div className={styles.tool}>
                  <p>
                    {line.length < 2
                      ? t("measure.lineTap", { count: 2 - line.length })
                      : t("measure.lineAdjust")}
                  </p>
                  <div className={styles.lengthRow}>
                    <TextField
                      label={t("measure.lengthMm")}
                      inputMode="decimal"
                      value={lengthMm}
                      onChange={(e) => setLengthMm(e.target.value)}
                    />
                    <IconButton
                      label={t("measure.clearLine")}
                      icon={<RotateCcw />}
                      onClick={() => setLine([])}
                      disabled={line.length === 0}
                    />
                  </div>
                </div>
              )}
              {addReference.error && <Notice kind="error">{addReference.error.message}</Notice>}
            </>
          )}

          {step === "mark" && (
            <>
              <p>{shape ? t("measure.markAdjust") : t("measure.markTap")}</p>
              {fit.isPending && (
                <p className="text-secondary" role="status">
                  {t("common.working")}
                </p>
              )}
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
                      {new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(preview.area_mm2)}{" "}
                      mm²
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
              <div className={styles.alternatives}>
                {shape?.type === "outline" && (
                  <IconButton label={t("measure.asCircle")} icon={<Circle />} showLabel onClick={asCircle} />
                )}
                <IconButton
                  label={t("measure.again")}
                  icon={<RotateCcw />}
                  showLabel
                  onClick={() => setShape(null)}
                  disabled={!shape}
                />
                <IconButton
                  label={t("measure.changeScale")}
                  icon={<Scaling />}
                  showLabel
                  onClick={() => setStep("scale")}
                />
              </div>
              {create.error && <Notice kind="error">{create.error.message}</Notice>}
              <p className={["text-secondary", styles.disclaimer].join(" ")}>{t("measure.disclaimer")}</p>
            </>
          )}
        </div>
      </div>
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
  circle: CircleShape;
  onChange: (c: CircleShape) => void;
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
