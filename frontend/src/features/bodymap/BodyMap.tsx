import { useRef, type KeyboardEvent, type MouseEvent } from "react";
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
  onSelectMarker?: (id: string) => void;
}

/** Flat silhouette divided into named zones. Zones are buttons; markers are dots at normalised positions. */
export function BodyMap({ view, markers = [], selectedZone, onSelectZone, onPlace, onSelectMarker }: Props) {
  const { t } = useTranslation();
  const svg = useRef<SVGSVGElement>(null);
  const zones = zonesForView(view);
  const zoneName = (zone: Zone) => t(`zones.${zone.code}`, { defaultValue: zone.name });

  function pointFromEvent(event: MouseEvent<SVGElement>, zone: Zone): MapPoint {
    const element = svg.current;
    const ctm = element?.getScreenCTM?.();
    if (element && ctm) {
      const inverse = ctm.inverse();
      const px = inverse.a * event.clientX + inverse.c * event.clientY + inverse.e;
      const py = inverse.b * event.clientX + inverse.d * event.clientY + inverse.f;
      return { zone: zone.code, x: clamp(px / MAP_WIDTH), y: clamp(py / MAP_HEIGHT) };
    }
    return anchorPoint(zone);
  }

  function activate(zone: Zone, point: MapPoint) {
    onSelectZone?.(zone);
    onPlace?.(point);
  }

  function onKey(event: KeyboardEvent<SVGPathElement>, zone: Zone) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      activate(zone, anchorPoint(zone));
    }
  }

  return (
    <svg
      ref={svg}
      className={styles.map}
      viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
      role="group"
      aria-label={t("bodymap.label", { view: t(`bodymap.views.${view}`) })}
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
      {markers.map((marker) => (
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
          <circle r={5.5} className={styles.markerHalo} />
          <circle r={3} />
        </g>
      ))}
    </svg>
  );
}

function anchorPoint(zone: Zone): MapPoint {
  return { zone: zone.code, x: zone.anchor[0] / MAP_WIDTH, y: zone.anchor[1] / MAP_HEIGHT };
}

function clamp(value: number): number {
  return Math.min(1, Math.max(0, Math.round(value * 10_000) / 10_000));
}
