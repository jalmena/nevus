import data from "./zones.json";

export type View = "front" | "back";
export type Side = "left" | "right" | "midline";
export type Region = "head" | "trunk" | "arm" | "leg";

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
}

interface BodyMapData {
  version: string;
  viewBox: [number, number, number, number];
  attribution: string;
  views: Record<View, { silhouette: string; zones: string[] }>;
  zones: Zone[];
}

export const bodyMap = data as BodyMapData;
export const VIEWS: View[] = ["front", "back"];
export const [, , MAP_WIDTH, MAP_HEIGHT] = bodyMap.viewBox;

const byCode = new Map(bodyMap.zones.map((zone) => [zone.code, zone]));

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
