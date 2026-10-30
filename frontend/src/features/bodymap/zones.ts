import data from "./zones.json";

export type View = "front" | "back" | "head" | "hands" | "feet";
export type Side = "left" | "right" | "midline";
export type Region = "head" | "trunk" | "arm" | "leg";
/** A part of a person's anatomy the front view can draw, each chosen on its own so any body can be drawn. */
export type BodyPart = "breasts" | "vulva" | "penis";

export interface Zone {
  code: string;
  view: View;
  side: Side;
  region: Region;
  name: string;
  molemapper_shape: number;
  path: string;
  anchor: [number, number];
  bbox: [number, number, number, number];
  /** A part of a person's anatomy: the zone shows, over the zones under it, only when the person has it. */
  part?: BodyPart;
}

interface BodyMapData {
  version: string;
  viewBox: [number, number, number, number];
  attribution: string;
  /** Per view: the outline, its zones and the landmarks drawn over them (nipples, navel, face, nails). */
  views: Record<
    View,
    {
      silhouette: string;
      zones: string[];
      details?: string;
      /** The front's anatomy, part by part, drawn over the one silhouette all bodies share. */
      details_by_part?: Partial<Record<BodyPart, string>>;
    }
  >;
  zones: Zone[];
}

export const bodyMap = data as BodyMapData;
export const VIEWS: View[] = ["front", "back", "head", "hands", "feet"];
export const [, , MAP_WIDTH, MAP_HEIGHT] = bodyMap.viewBox;

const byCode = new Map(bodyMap.zones.map((zone) => [zone.code, zone]));

/**
 * Front and back only sketch the head and the hands, and the front the feet: each has a view of its own, so a tap
 * there opens that view instead of placing a mark. The back's heels are zones: the feet's view does not show them.
 * Marks placed on a sketch before still show where they were put.
 */
export const SKETCHED: Readonly<Record<string, View>> = {
  "1100": "head",
  "2100": "head",
  "1850": "hands",
  "1851": "hands",
  "2850": "hands",
  "2851": "hands",
  "1600": "feet",
  "1601": "feet",
};

export function zonesForView(view: View): Zone[] {
  return bodyMap.zones.filter((zone) => zone.view === view);
}

export function zoneByCode(code: string): Zone | undefined {
  return byCode.get(code);
}

/** A location on the map: a zone plus a point normalised to the view box (0..1), as the backend stores it. */
export interface MapPoint {
  zone: string;
  x: number;
  y: number;
}
