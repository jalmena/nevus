import {
  Fragment,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type MouseEvent,
  type PointerEvent,
  type WheelEvent,
} from "react";
import { Expand, ZoomIn, ZoomOut } from "lucide-react";
import { useTranslation } from "react-i18next";
import {
  MAP_HEIGHT,
  MAP_WIDTH,
  SKETCHED,
  bodyMap,
  zoneByCode,
  zonesForView,
  type MapPoint,
  type BodyPart,
  type View,
  type Zone,
} from "./zones";
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
  /** The tapped zone; null when the selected zone is tapped again or the tap lands outside the body. */
  onSelectZone?: (zone: Zone | null) => void;
  /** When set, a tap inside a zone also yields the tapped point; the keyboard places at the zone's anchor. */
  onPlace?: (point: MapPoint) => void;
  /** While a mark is being placed, the first tap on a zone zooms in on it and the second places the mark. */
  placing?: boolean;
  onSelectMarker?: (id: string) => void;
  /** A tap on the head, a hand or a foot sketched on the front or the back: open that part's own view. */
  onOpenView?: (view: View) => void;
  /** The parts of the person's anatomy to draw on the front; none draws the body without them. */
  anatomy?: BodyPart[];
}

interface ViewBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

/**
 * The part of the map a view fills: the full width, and the height of its zones with some room. Front and back
 * fill the whole map; the head, hands and feet are shorter, so framing them makes them larger on screen.
 */
function homeOf(view: View): ViewBox {
  const zones = zonesForView(view);
  const room = 12;
  const y = Math.max(0, Math.min(...zones.map((zone) => zone.bbox[1])) - room);
  const bottom = Math.min(MAP_HEIGHT, Math.max(...zones.map((zone) => zone.bbox[3])) + room);
  return { x: 0, y, w: MAP_WIDTH, h: bottom - y };
}

/** The backs of the hands and the tops of the feet, the upper row of their views, tinted apart from the palms and soles. */
const REVERSE = new Set(["3220", "3221", "3320", "3321"]);

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

/** A view box kept inside the view's frame and at its proportions, between the whole frame and the deepest zoom. */
function clamp(vb: ViewBox, home: ViewBox): ViewBox {
  const w = Math.min(home.w, Math.max(home.w / MAX_ZOOM, vb.w));
  const h = (w * home.h) / home.w;
  return {
    w,
    h,
    x: Math.min(Math.max(home.x, vb.x), home.x + home.w - w),
    y: Math.min(Math.max(home.y, vb.y), home.y + home.h - h),
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
  onOpenView,
  anatomy = [],
}: Props) {
  const { t } = useTranslation();
  const svg = useRef<SVGSVGElement>(null);
  const home = homeOf(view);
  const [vb, setVb] = useState<ViewBox>(home);
  const [focused, setFocused] = useState<string | null>(null);
  const [screenWidth, setScreenWidth] = useState(400);
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const pinch = useRef<{ dist: number; vb: ViewBox } | null>(null);
  const moved = useRef(false);
  // The anatomy's zones lie over the zones under them, so they come last and only for the parts the person has.
  const zones = zonesForView(view)
    .filter((zone) => !zone.part || anatomy.includes(zone.part))
    .sort((a, b) => Number(Boolean(a.part)) - Number(Boolean(b.part)));
  const zoneName = (zone: Zone) => t(`zones.${zone.code}`, { defaultValue: zone.name });

  useEffect(() => {
    setVb(homeOf(view));
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
      return clamp(
        {
          x: centre.x - (centre.x - current.x) / factor,
          y: centre.y - (centre.y - current.y) / factor,
          w: current.w / factor,
          h: current.h / factor,
        },
        home,
      );
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
    const w = Math.max((right - left) * room, ((bottom - top) * room * home.w) / home.h, home.w / MAX_ZOOM);
    const h = (w * home.h) / home.w;
    setVb(clamp({ x: (left + right) / 2 - w / 2, y: (top + bottom) / 2 - h / 2, w, h }, home));
    setFocused(zone.code);
  }

  /** Whether the zone already takes a good part of the view, so a tap on it is precise enough. */
  function closeEnough(zone: Zone): boolean {
    const [left, top, right, bottom] = zone.bbox;
    return Math.max((right - left) / vb.w, (bottom - top) / vb.h) >= 0.4;
  }

  function activate(zone: Zone, point: MapPoint) {
    if (moved.current) return; // that was a drag, not a tap
    if (!placing && zone.code === selectedZone) {
      onSelectZone?.(null); // the same zone again: nothing selected
      return;
    }
    onSelectZone?.(zone);
    if (placing && focused !== zone.code && !closeEnough(zone)) {
      zoomToZone(zone);
      return;
    }
    onPlace?.(point);
  }

  /** A tap on the background (the silhouette or the space around it): nothing selected any more. */
  function onBackgroundClick(event: MouseEvent<SVGSVGElement>) {
    if (moved.current || (event.target as Element).closest("[data-zone]")) return;
    onSelectZone?.(null);
    if (placing && focused) showAll();
  }

  // Placing starts with a zone already selected: zoom in on it, so the next tap is the precise one.
  const [wasPlacing, setWasPlacing] = useState(placing);
  if (placing !== wasPlacing) {
    setWasPlacing(placing);
    const zone = placing && selectedZone ? zoneByCode(selectedZone) : undefined;
    if (zone && !closeEnough(zone)) zoomToZone(zone);
  }

  function onKey(event: KeyboardEvent<SVGPathElement>, zone: Zone) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      activate(zone, anchorPoint(zone));
    }
  }

  function showAll() {
    setVb(home);
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
        clamp(
          {
            x: mid.x - (mid.x - start.x) / factor,
            y: mid.y - (mid.y - start.y) / factor,
            w: start.w / factor,
            h: start.h / factor,
          },
          home,
        ),
      );
      return;
    }
    const dx = event.clientX - previous.x;
    const dy = event.clientY - previous.y;
    if (vb.w < home.w && (moved.current || Math.hypot(dx, dy) > 4)) {
      moved.current = true;
      setVb((current) => clamp({ ...current, x: current.x - dx * unit, y: current.y - dy * unit }, home));
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
    const w = Math.max(Math.max(...xs) - Math.min(...xs) + 2 * pad, home.w / MAX_ZOOM);
    const h = (w * home.h) / home.w;
    setVb(
      clamp(
        {
          x: (Math.min(...xs) + Math.max(...xs)) / 2 - w / 2,
          y: (Math.min(...ys) + Math.max(...ys)) / 2 - h / 2,
          w,
          h,
        },
        home,
      ),
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
        onClick={onBackgroundClick}
      >
        <path className={styles.silhouette} d={bodyMap.views[view].silhouette} />
        {zones.map((zone) => {
          const elsewhere = SKETCHED[zone.code];
          if (elsewhere) {
            const name = t(`bodymap.views.${elsewhere}`);
            const open = () => onOpenView?.(elsewhere);
            return onOpenView ? (
              <path
                key={zone.code}
                d={zone.path}
                className={styles.sketched}
                role="button"
                tabIndex={0}
                aria-label={name}
                data-zone={zone.code}
                onClick={() => !moved.current && open()}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    open();
                  }
                }}
              >
                <title>{name}</title>
              </path>
            ) : (
              <path key={zone.code} d={zone.path} className={styles.sketched} aria-hidden="true" />
            );
          }
          return (
            <Fragment key={zone.code}>
              {/* The anatomy lies over what is under it, the gap between the legs included. */}
              {zone.part && (
                <path className={styles.partBase} d={zone.path} aria-hidden="true" data-under={zone.code} />
              )}
              <path
                d={zone.path}
                className={[
                  styles.zone,
                  zone.code === selectedZone ? styles.selected : "",
                  REVERSE.has(zone.code) ? styles.reverse : "",
                ].join(" ")}
                role="button"
                tabIndex={0}
                aria-label={zoneName(zone)}
                aria-pressed={zone.code === selectedZone}
                data-zone={zone.code}
                onClick={(event) => activate(zone, pointFromEvent(event, zone))}
                onKeyDown={(event) => onKey(event, zone)}
              >
                <title>{zoneName(zone)}</title>
              </path>
            </Fragment>
          );
        })}
        {bodyMap.views[view].details && (
          <path className={styles.details} d={bodyMap.views[view].details} aria-hidden="true" />
        )}
        {anatomy.map((part) => {
          const d = bodyMap.views[view].details_by_part?.[part];
          return d ? <path key={part} className={styles.details} d={d} aria-hidden="true" /> : null;
        })}
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
        <button
          type="button"
          onClick={() => zoom(1.5)}
          aria-label={t("bodymap.zoomIn")}
          title={t("bodymap.zoomIn")}
        >
          <ZoomIn aria-hidden="true" />
        </button>
        {vb.w < home.w && (
          <button
            type="button"
            onClick={() => zoom(1 / 1.5)}
            aria-label={t("bodymap.zoomOut")}
            title={t("bodymap.zoomOut")}
          >
            <ZoomOut aria-hidden="true" />
          </button>
        )}
        {vb.w < home.w && (
          <button
            type="button"
            onClick={showAll}
            aria-label={t("bodymap.zoomReset")}
            title={t("bodymap.zoomReset")}
          >
            <Expand aria-hidden="true" />
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
