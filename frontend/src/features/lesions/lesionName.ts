import type { TFunction } from "i18next";
import type { LesionOut } from "@/lib/lesions";

/** The label if the person gave one, else the zone's name; and "zone · view" as the location line. */
export function lesionTitle(lesion: LesionOut, t: TFunction): string {
  return lesion.label ?? zoneName(lesion.location.zone, t);
}

/** Every zone of the body map is named in each catalogue (a test checks it), so no geometry is needed here. */
export function zoneName(code: string, t: TFunction): string {
  return t(`zones.${code}`, { defaultValue: code });
}

export function locationLine(lesion: LesionOut, t: TFunction): string {
  return t("bodymap.selected", {
    zone: zoneName(lesion.location.zone, t),
    view: t(`bodymap.views.${lesion.location.view}`),
  });
}
