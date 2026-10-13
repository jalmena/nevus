import type { TFunction } from "i18next";
import { Calendar, CalendarPlus, FileText, PersonStanding, ScanLine, User } from "lucide-react";
import type { Chrome } from "@/app/chrome";

/** The desktop rail's context block while inside a person: the body map and the five tools. */
export function personRail(t: TFunction, personId: string, name: string | undefined): Chrome["rail"] {
  const base = `/persons/${personId}`;
  return {
    heading: name ?? "…",
    items: [
      { to: base, end: true, label: t("bodymap.title"), icon: <PersonStanding /> },
      { to: `${base}/appointments`, label: t("appointments.sectionTitle"), icon: <Calendar /> },
      { to: `${base}/sessions`, label: t("sessions.title"), icon: <ScanLine /> },
      { to: `${base}/reports`, label: t("reports.title"), icon: <FileText /> },
      { to: `${base}/calendar`, label: t("calendar.title"), icon: <CalendarPlus /> },
      { to: `${base}/profile`, label: t("persons.profile"), icon: <User /> },
    ],
  };
}
