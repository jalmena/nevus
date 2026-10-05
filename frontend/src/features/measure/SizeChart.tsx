import { useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Segmented } from "@/design-system/components/Segmented";
import { useSession } from "@/lib/auth/session";
import { formatMm, useLesionMeasurements, type Measurement } from "@/lib/measurements";
import styles from "./SizeChart.module.css";

const HEIGHT = 220;
const MARGIN = { top: 30, right: 16, bottom: 28, left: 40 };
const STEPS = [0.1, 0.2, 0.25, 0.5, 1, 2, 2.5, 5, 10, 20];
type Metric = "longest" | "area" | "compactness" | "contrast";
const ALL_METRICS: readonly Metric[] = ["longest", "area", "compactness", "contrast"];

/**
 * What each series plots. The span floor keeps measurement noise from looking like a slope. The
 * descriptors exist only for measurements saved since they do, so their series may be shorter.
 */
const METRICS: Record<
  Metric,
  { value: (m: Measurement) => number | null; sigma: (m: Measurement) => number; floor: number; unit: string }
> = {
  longest: { value: (m) => m.longest_mm, sigma: (m) => m.sigma_longest_mm, floor: 2, unit: "mm" },
  area: { value: (m) => m.area_mm2, sigma: (m) => m.sigma_area_mm2, floor: 8, unit: "mm²" },
  compactness: {
    value: (m) => m.descriptors?.shape.compactness ?? null,
    sigma: () => 0,
    floor: 0.2,
    unit: "",
  },
  contrast: { value: (m) => m.descriptors?.colour?.contrast ?? null, sigma: () => 0, floor: 10, unit: "ΔE" },
};

/**
 * The values with their uncertainty, never below zero, and never narrower than the floor or 40 % of
 * the typical value: a 0.2 mm wobble on a 5 mm mark must not fill the chart's height.
 */
export function yDomain(points: { value: number; sigma: number }[], floor = 2): [number, number] {
  let lo = Math.min(...points.map((p) => p.value - p.sigma));
  let hi = Math.max(...points.map((p) => p.value + p.sigma));
  const mean = points.reduce((sum, p) => sum + p.value, 0) / Math.max(points.length, 1);
  const minSpan = Math.max(floor, 0.4 * mean);
  if (hi - lo < minSpan) {
    const mid = (lo + hi) / 2;
    lo = mid - minSpan / 2;
    hi = mid + minSpan / 2;
  }
  if (lo < 0) {
    hi -= lo;
    lo = 0;
  }
  return [lo, hi];
}

/** Round tick values covering [min, max] with at most `count` steps. */
export function niceTicks(min: number, max: number, count = 4): { ticks: number[]; lo: number; hi: number } {
  const span = Math.max(max - min, 1e-6);
  const step = STEPS.find((s) => span / s <= count) ?? STEPS[STEPS.length - 1] ?? 1;
  const lo = Math.floor(min / step + 1e-9) * step;
  const hi = Math.ceil(max / step - 1e-9) * step;
  const ticks: number[] = [];
  for (let value = lo; value <= hi + step / 2; value += step) ticks.push(Number(value.toFixed(3)));
  return { ticks, lo, hi };
}

/** Above the point and its band so the line stays visible, below it near the top, inside the chart at the edges. */
function tooltipPlacement(point: { x: number; up: number; down: number }, width: number) {
  const below = point.up < 70;
  const horizontal = point.x < 90 ? "-24px" : point.x > width - 90 ? "calc(-100% + 24px)" : "-50%";
  return {
    left: point.x,
    top: below ? point.down : point.up,
    transform: `translate(${horizontal}, ${below ? "10px" : "calc(-100% - 10px)"})`,
  };
}

function formatArea(value: number, sigma: number, locale: string, showUncertainty: boolean): string {
  const format = new Intl.NumberFormat(locale, { maximumFractionDigits: 1, minimumFractionDigits: 1 });
  return showUncertainty
    ? `${format.format(value)} ± ${format.format(Math.max(sigma, 0.1))} mm²`
    : `${format.format(value)} mm²`;
}

/** The longest diameter at each visit, with its uncertainty as a band. A table and a CSV carry the same numbers. */
export function SizeChart({ lesionId }: { lesionId: string }) {
  const { t, i18n } = useTranslation();
  const measurements = useLesionMeasurements(lesionId);
  const session = useSession();
  const showUncertainty = session.data?.user.show_uncertainty ?? true;
  const locale = i18n.resolvedLanguage ?? "en";
  const [asTable, setAsTable] = useState(false);
  const [chosen, setMetric] = useState<Metric>("longest");
  const [active, setActive] = useState<number | null>(null);
  const wrapper = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(600);
  const series: Measurement[] = measurements.data ?? [];
  const available = ALL_METRICS.filter(
    (key) => series.filter((m) => METRICS[key].value(m) !== null).length >= 2,
  );
  const metric: Metric = available.includes(chosen) ? chosen : "longest";
  const plotted = METRICS[metric];
  const shown = series.filter((m) => plotted.value(m) !== null);
  const drawn = series.length >= 2 && !asTable;

  useEffect(() => {
    const element = wrapper.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => setWidth(element.clientWidth || 600));
    observer.observe(element);
    return () => observer.disconnect();
  }, [drawn]);

  if (series.length < 2) return null; // one visit: the latest size above already says it all

  const longDate = new Intl.DateTimeFormat(locale, { dateStyle: "medium" });
  const two = new Intl.NumberFormat(locale, { maximumFractionDigits: 2, minimumFractionDigits: 2 });
  const whole = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
  const times = shown.map((m) => new Date(m.captured_at).getTime());
  const t0 = Math.min(...times);
  const t1 = Math.max(...times);
  const shortDate = new Intl.DateTimeFormat(
    locale,
    t1 - t0 > 120 * 86_400_000 ? { month: "short", year: "numeric" } : { day: "numeric", month: "short" },
  );
  const plotW = Math.max(width - MARGIN.left - MARGIN.right, 60);
  const plotH = HEIGHT - MARGIN.top - MARGIN.bottom;
  const pad = Math.min(24, plotW * 0.05);
  const x = (time: number) =>
    MARGIN.left + pad + (t1 === t0 ? (plotW - 2 * pad) / 2 : ((time - t0) / (t1 - t0)) * (plotW - 2 * pad));
  const valueOf = (m: Measurement) => plotted.value(m) ?? 0;
  const sigmaOf = (m: Measurement) => (showUncertainty ? plotted.sigma(m) : 0);
  const unit = plotted.unit;
  const format = (m: Measurement) => {
    if (metric === "area") return formatArea(m.area_mm2, m.sigma_area_mm2, locale, showUncertainty);
    if (metric === "longest") return formatMm(m.longest_mm, m.sigma_longest_mm, locale, showUncertainty);
    const number = metric === "compactness" ? two.format(valueOf(m)) : whole.format(valueOf(m));
    return unit ? `${number} ${unit}` : number;
  };
  const [lo0, hi0] = yDomain(
    shown.map((m) => ({ value: valueOf(m), sigma: sigmaOf(m) })),
    plotted.floor,
  );
  const { ticks, lo, hi } = niceTicks(lo0, hi0);
  const y = (value: number) => MARGIN.top + plotH - ((value - lo) / (hi - lo)) * plotH;
  const points = shown.map((m, index) => ({
    m,
    x: x(times[index] ?? t0),
    y: y(valueOf(m)),
    up: y(valueOf(m) + sigmaOf(m)),
    down: y(valueOf(m) - sigmaOf(m)),
  }));
  const line = points.map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  const band = [
    ...points.map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)},${p.up.toFixed(1)}`),
    ...[...points].reverse().map((p) => `L${p.x.toFixed(1)},${p.down.toFixed(1)}`),
    "Z",
  ].join(" ");
  const dateLabel = (p: (typeof points)[number]) => shortDate.format(new Date(p.m.captured_at));
  const labelled: number[] = [];
  points.forEach((p, i) => {
    const last = labelled.at(-1);
    const previous = last === undefined ? undefined : points[last];
    if (!previous || (p.x - previous.x >= 84 && dateLabel(p) !== dateLabel(previous))) labelled.push(i);
  });
  const final = points.at(-1);
  const lastLabelled = points[labelled.at(-1) ?? 0];
  if (final && lastLabelled && final !== lastLabelled && dateLabel(final) !== dateLabel(lastLabelled)) {
    if (labelled.length > 1 && final.x - lastLabelled.x < 84) labelled.pop();
    labelled.push(points.length - 1);
  }
  const tickFormat = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 });
  const describe = (m: Measurement) => `${longDate.format(new Date(m.captured_at))}: ${format(m)}`;
  const current = active === null ? null : points[active];
  const focused = shown[active ?? shown.length - 1];

  function nearest(event: PointerEvent<SVGSVGElement>): number {
    const left = event.currentTarget.getBoundingClientRect().left;
    const at = event.clientX - left;
    let best = 0;
    points.forEach((p, i) => {
      if (Math.abs(p.x - at) < Math.abs((points[best]?.x ?? 0) - at)) best = i;
    });
    return best;
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const last = points.length - 1;
    const from = active ?? last;
    const moves: Record<string, number> = {
      ArrowLeft: Math.max(0, from - 1),
      ArrowRight: Math.min(last, from + 1),
      Home: 0,
      End: last,
    };
    if (event.key === "Escape") setActive(null);
    else if (event.key in moves) setActive(moves[event.key] ?? from);
    else return;
    event.preventDefault();
  }

  return (
    <section className={styles.section} aria-labelledby="size-heading">
      <h2 id="size-heading">{t("chart.title")}</h2>
      <p className="text-secondary">{showUncertainty ? t("chart.subtitleBand") : t("chart.subtitle")}</p>
      {!asTable && (
        <Segmented
          wide
          label={t("chart.metric")}
          options={available.map((value) => ({
            value,
            label: t(`chart.metrics.${value}`),
          }))}
          value={metric}
          onChange={setMetric}
        />
      )}
      {asTable ? (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col">{t("chart.date")}</th>
                <th scope="col">{t("measure.longest")}</th>
                <th scope="col">{t("measure.across")}</th>
                <th scope="col">{t("measure.area")}</th>
                <th scope="col">{t("measure.compactness")}</th>
                <th scope="col">{t("measure.contrast")}</th>
              </tr>
            </thead>
            <tbody>
              {series.map((m) => (
                <tr key={m.id}>
                  <td className="numeric">{longDate.format(new Date(m.captured_at))}</td>
                  <td className="numeric">
                    {formatMm(m.longest_mm, m.sigma_longest_mm, locale, showUncertainty)}
                  </td>
                  <td className="numeric">
                    {formatMm(m.perpendicular_mm, m.sigma_perpendicular_mm, locale, showUncertainty)}
                  </td>
                  <td className="numeric">
                    {formatArea(m.area_mm2, m.sigma_area_mm2, locale, showUncertainty)}
                  </td>
                  <td className="numeric">
                    {m.descriptors ? two.format(m.descriptors.shape.compactness) : "—"}
                  </td>
                  <td className="numeric">
                    {m.descriptors?.colour ? `${whole.format(m.descriptors.colour.contrast)} ΔE` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {series.some((m) => m.descriptors) && (
            <p className="text-secondary">{t("chart.descriptorsNote")}</p>
          )}
        </div>
      ) : (
        <div
          ref={wrapper}
          className={styles.chart}
          role="slider"
          aria-roledescription={t("chart.roleDescription")}
          aria-label={t("chart.label", { metric: t(`chart.metrics.${metric}`), count: shown.length })}
          aria-valuemin={1}
          aria-valuemax={points.length}
          aria-valuenow={(active ?? points.length - 1) + 1}
          aria-valuetext={focused ? describe(focused) : undefined}
          tabIndex={0}
          onKeyDown={onKeyDown}
          onFocus={() => setActive((value) => value ?? points.length - 1)}
          onBlur={() => setActive(null)}
        >
          <svg
            width={width}
            height={HEIGHT}
            viewBox={`0 0 ${width} ${HEIGHT}`}
            aria-hidden="true"
            onPointerMove={(event) => setActive(nearest(event))}
            onPointerLeave={() => setActive(null)}
          >
            <text className={styles.unit} x={MARGIN.left - 8} y={MARGIN.top - 16} textAnchor="end">
              {unit}
            </text>
            {ticks.map((value) => (
              <g key={value}>
                <line
                  className={styles.grid}
                  x1={MARGIN.left}
                  x2={width - MARGIN.right}
                  y1={y(value)}
                  y2={y(value)}
                />
                <text className={styles.axis} x={MARGIN.left - 8} y={y(value)} dy="0.32em" textAnchor="end">
                  {tickFormat.format(value)}
                </text>
              </g>
            ))}
            {labelled.map((index) => {
              const p = points[index];
              if (!p) return null;
              return (
                <text key={p.m.id} className={styles.axis} x={p.x} y={HEIGHT - 8} textAnchor="middle">
                  {dateLabel(p)}
                </text>
              );
            })}
            {showUncertainty && <path className={styles.band} d={band} />}
            {current && (
              <line
                className={styles.crosshair}
                x1={current.x}
                x2={current.x}
                y1={MARGIN.top}
                y2={MARGIN.top + plotH}
              />
            )}
            <path className={styles.line} d={line} />
            {points.map((p, index) => (
              <circle key={p.m.id} className={styles.marker} cx={p.x} cy={p.y} r={index === active ? 6 : 4} />
            ))}
          </svg>
          {current && (
            <div className={styles.tooltip} style={tooltipPlacement(current, width)}>
              <span className={styles.tooltipDate}>{longDate.format(new Date(current.m.captured_at))}</span>
              <span className="numeric">{format(current.m)}</span>
            </div>
          )}
        </div>
      )}
      <div className={styles.actions}>
        <Button variant="secondary" onClick={() => setAsTable((value) => !value)}>
          {asTable ? t("chart.showChart") : t("chart.showTable")}
        </Button>
        <a href={`/api/lesions/${lesionId}/measurements.csv`} download>
          {t("chart.csv")}
        </a>
      </div>
    </section>
  );
}
