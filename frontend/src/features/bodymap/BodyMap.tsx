import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type MouseEvent,
  type PointerEvent,
  type WheelEvent,
} from "react";
import { useTranslation } from "react-i18next";
import { MAP_HEIGHT, MAP_WIDTH, bodyMap, zonesForView, type MapPoint, type View, type Zone } from "./zones";
import styles from "./BodyMap.module.css";

export interface Marker {
  id: string;
  x: number;
  y: number;
  label: string;
  due?: boolean;
  selected?: boolean;
}

interface Props {
  view: View;
  markers?: Marker[];
  selectedZone?: string | null;
  onSelectZone?: (zone: Zone) => void;
  /** When set, a tap inside a zone also yields the tapped point; the keyboard places at the zone's anchor. */
  onPlace?: (point: MapPoint) => void;
  /** While a mark is being placed, the first tap on a zone zooms in on it and the second places the mark. */
  placing?: boolean;
  onSelectMarker?: (id: string) => void;
}

interface ViewBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

const FULL: ViewBox = { x: 0, y: 0, w: MAP_WIDTH, h: MAP_HEIGHT };
const MAX_ZOOM = 6;
const CLUSTER_PX = 18;

interface Cluster {
  x: number;
  y: number;
  members: Marker[];
}

/** Greedy clustering in screen space: markers closer than CLUSTER_PX on screen share one badge. */
function cluster(markers: Marker[], unit: number): Cluster[] {
  const threshold = CLUSTER_PX * unit;
  const out: Cluster[] = [];
  for (const marker of markers) {
    const x = marker.x * MAP_WIDTH;
    const y = marker.y * MAP_HEIGHT;
    const near = out.find((c) => Math.hypot(c.x - x, c.y - y) < threshold);
    if (near) {
      near.members.push(marker);
      near.x = near.members.reduce((sum, m) => sum + m.x * MAP_WIDTH, 0) / near.members.length;
      near.y = near.members.reduce((sum, m) => sum + m.y * MAP_HEIGHT, 0) / near.members.length;
    } else {
      out.push({ x, y, members: [marker] });
    }
  }
  return out;
}

function clamp(vb: ViewBox): ViewBox {
  const w = Math.min(MAP_WIDTH, Math.max(MAP_WIDTH / MAX_ZOOM, vb.w));
  const h = (w * MAP_HEIGHT) / MAP_WIDTH;
  return {
    w,
    h,
    x: Math.min(Math.max(0, vb.x), MAP_WIDTH - w),
    y: Math.min(Math.max(0, vb.y), MAP_HEIGHT - h),
  };
}

/** Flat silhouette divided into named zones, with zoom, pan and clustered markers. */
export function BodyMap({
  view,
  markers = [],
  selectedZone,
  onSelectZone,
  onPlace,
  placing = false,
  onSelectMarker,
}: Props) {
  const { t } = useTranslation();
  const svg = useRef<SVGSVGElement>(null);
  const [vb, setVb] = useState<ViewBox>(FULL);
  const [focused, setFocused] = useState<string | null>(null);
  const [screenWidth, setScreenWidth] = useState(400);
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const pinch = useRef<{ dist: number; vb: ViewBox } | null>(null);
  const moved = useRef(false);
  const zones = zonesForView(view);
  const zoneName = (zone: Zone) => t(`zones.${zone.code}`, { defaultValue: zone.name });

  useEffect(() => {
    setVb(FULL);
    setFocused(null);
  }, [view]);
  useEffect(() => {
    const element = svg.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => setScreenWidth(element.clientWidth || 400));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const unit = vb.w / Math.max(screenWidth, 1);
  const scale = vb.w / MAP_WIDTH;

  function toMap(clientX: number, clientY: number): { x: number; y: number } | null {
    const ctm = svg.current?.getScreenCTM?.();
    if (!ctm) return null;
    const inverse = ctm.inverse();
    return {
      x: inverse.a * clientX + inverse.c * clientY + inverse.e,
      y: inverse.b * clientX + inverse.d * clientY + inverse.f,
    };
  }

  function zoom(factor: number, at?: { x: number; y: number }) {
    setVb((current) => {
      const centre = at ?? { x: current.x + current.w / 2, y: current.y + current.h / 2 };
      return clamp({
        x: centre.x - (centre.x - current.x) / factor,
        y: centre.y - (centre.y - current.y) / factor,
        w: current.w / factor,
        h: current.h / factor,
      });
    });
  }

  function pointFromEvent(event: MouseEvent<SVGElement>, zone: Zone): MapPoint {
    const p = toMap(event.clientX, event.clientY);
    if (!p) return anchorPoint(zone);
    return { zone: zone.code, x: round(p.x / MAP_WIDTH), y: round(p.y / MAP_HEIGHT) };
  }

  /** The view that shows one zone large, with room around it, so the next tap lands where the mark is. */
  function zoomToZone(zone: Zone) {
    const [left, top, right, bottom] = zone.bbox;
    const room = 1.3;
    const w = Math.max(
      (right - left) * room,
      ((bottom - top) * room * MAP_WIDTH) / MAP_HEIGHT,
      MAP_WIDTH / MAX_ZOOM,
    );
    const h = (w * MAP_HEIGHT) / MAP_WIDTH;
    setVb(clamp({ x: (left + right) / 2 - w / 2, y: (top + bottom) / 2 - h / 2, w, h }));
    setFocused(zone.code);
  }

  /** Whether the zone already takes a good part of the view, so a tap on it is precise enough. */
  function closeEnough(zone: Zone): boolean {
    const [left, top, right, bottom] = zone.bbox;
    return Math.max((right - left) / vb.w, (bottom - top) / vb.h) >= 0.4;
  }

  function activate(zone: Zone, point: MapPoint) {
    if (moved.current) return; // that was a drag, not a tap
    onSelectZone?.(zone);
    if (placing && focused !== zone.code && !closeEnough(zone)) {
      zoomToZone(zone);
      return;
    }
    onPlace?.(point);
  }

  function onKey(event: KeyboardEvent<SVGPathElement>, zone: Zone) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      activate(zone, anchorPoint(zone));
    }
  }

  function showAll() {
    setVb(FULL);
    setFocused(null);
  }

  function onWheel(event: WheelEvent<SVGSVGElement>) {
    const at = toMap(event.clientX, event.clientY) ?? undefined;
    zoom(event.deltaY < 0 ? 1.25 : 0.8, at);
  }

  function onPointerDown(event: PointerEvent<SVGSVGElement>) {
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    moved.current = false;
    const [a, b] = [...pointers.current.values()];
    pinch.current = a && b ? { dist: Math.hypot(a.x - b.x, a.y - b.y), vb } : null;
  }

  function onPointerMove(event: PointerEvent<SVGSVGElement>) {
    const previous = pointers.current.get(event.pointerId);
    if (!previous) return;
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pointers.current.size === 2 && pinch.current) {
      const [a, b] = [...pointers.current.values()];
      if (!a || !b) return;
      moved.current = true;
      const factor = Math.hypot(a.x - b.x, a.y - b.y) / Math.max(pinch.current.dist, 1);
      const start = pinch.current.vb;
      const mid = toMap((a.x + b.x) / 2, (a.y + b.y) / 2) ?? {
        x: start.x + start.w / 2,
        y: start.y + start.h / 2,
      };
      setVb(
        clamp({
          x: mid.x - (mid.x - start.x) / factor,
          y: mid.y - (mid.y - start.y) / factor,
          w: start.w / factor,
          h: start.h / factor,
        }),
      );
      return;
    }
    const dx = event.clientX - previous.x;
    const dy = event.clientY - previous.y;
    if (vb.w < MAP_WIDTH && (moved.current || Math.hypot(dx, dy) > 4)) {
      moved.current = true;
      setVb((current) => clamp({ ...current, x: current.x - dx * unit, y: current.y - dy * unit }));
    }
  }

  function onPointerUp(event: PointerEvent<SVGSVGElement>) {
    pointers.current.delete(event.pointerId);
    if (pointers.current.size < 2) pinch.current = null;
    // Let the click that follows this pointerup see whether it was a drag, then forget.
    window.setTimeout(() => (moved.current = false), 0);
  }

  function expand(group: Cluster) {
    const xs = group.members.map((m) => m.x * MAP_WIDTH);
    const ys = group.members.map((m) => m.y * MAP_HEIGHT);
    const pad = 12;
    const w = Math.max(Math.max(...xs) - Math.min(...xs) + 2 * pad, MAP_WIDTH / MAX_ZOOM);
    const h = (w * MAP_HEIGHT) / MAP_WIDTH;
    setVb(
      clamp({
        x: (Math.min(...xs) + Math.max(...xs)) / 2 - w / 2,
        y: (Math.min(...ys) + Math.max(...ys)) / 2 - h / 2,
        w,
        h,
      }),
    );
  }

  const groups = cluster(markers, unit);
  return (
    <div className={styles.wrapper}>
      <svg
        ref={svg}
        className={styles.map}
        viewBox={`${vb.x} ${vb.y} ${vb.w} ${vb.h}`}
        role="group"
        aria-label={t("bodymap.label", { view: t(`bodymap.views.${view}`) })}
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <path className={styles.silhouette} d={bodyMap.views[view].silhouette} />
        {zones.map((zone) => (
          <path
            key={zone.code}
            d={zone.path}
            className={[styles.zone, zone.code === selectedZone ? styles.selected : ""].join(" ")}
            role="button"
            tabIndex={0}
            aria-label={zoneName(zone)}
            aria-pressed={zone.code === selectedZone}
            data-zone={zone.code}
            onClick={(event) => activate(zone, pointFromEvent(event, zone))}
            onKeyDown={(event) => onKey(event, zone)}
          />
        ))}
        {groups.map((group) =>
          group.members.length > 1 ? (
            <g
              key={group.members.map((m) => m.id).join("-")}
              className={styles.cluster}
              transform={`translate(${group.x} ${group.y})`}
              role="button"
              tabIndex={0}
              aria-label={t("bodymap.cluster", { count: group.members.length })}
              onClick={(event) => {
                event.stopPropagation();
                expand(group);
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  expand(group);
                }
              }}
            >
              <circle
                r={8 * scale}
                className={[
                  styles.clusterDot,
                  group.members.some((m) => m.due) ? styles.clusterDotDue : "",
                ].join(" ")}
              />
              <text
                textAnchor="middle"
                dy={3.2 * scale}
                fontSize={9 * scale}
                className={[
                  styles.clusterCount,
                  group.members.some((m) => m.due) ? styles.clusterCountDue : "",
                ].join(" ")}
              >
                {group.members.length}
              </text>
            </g>
          ) : (
            group.members.map((marker) => (
              <g
                key={marker.id}
                className={[
                  styles.marker,
                  marker.due ? styles.due : "",
                  marker.selected ? styles.markerSelected : "",
                ].join(" ")}
                transform={`translate(${marker.x * MAP_WIDTH} ${marker.y * MAP_HEIGHT})`}
                role={onSelectMarker ? "button" : undefined}
                tabIndex={onSelectMarker ? 0 : undefined}
                aria-label={marker.label}
                onClick={(event) => {
                  event.stopPropagation();
                  onSelectMarker?.(marker.id);
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelectMarker?.(marker.id);
                  }
                }}
              >
                <circle r={5.5 * scale} className={styles.markerHalo} />
                <circle r={3 * scale} />
              </g>
            ))
          ),
        )}
      </svg>
      <div className={styles.zoom}>
        <button type="button" onClick={() => zoom(1.5)} aria-label={t("bodymap.zoomIn")}>
          +
        </button>
        <button
          type="button"
          onClick={() => zoom(1 / 1.5)}
          aria-label={t("bodymap.zoomOut")}
          disabled={vb.w >= MAP_WIDTH}
        >
          −
        </button>
        {vb.w < MAP_WIDTH && (
          <button type="button" onClick={showAll} aria-label={t("bodymap.zoomReset")}>
            ⤢
          </button>
        )}
      </div>
    </div>
  );
}

function anchorPoint(zone: Zone): MapPoint {
  return { zone: zone.code, x: zone.anchor[0] / MAP_WIDTH, y: zone.anchor[1] / MAP_HEIGHT };
}

function round(value: number): number {
  return Math.min(1, Math.max(0, Math.round(value * 10_000) / 10_000));
}
