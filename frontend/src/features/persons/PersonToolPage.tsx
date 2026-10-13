import { useTranslation } from "react-i18next";
import { useParams } from "react-router";
import { Notice } from "@/design-system/components/Notice";
import { PrepareAppointment } from "@/features/appointments/PrepareAppointment";
import { lesionTitle } from "@/features/lesions/lesionName";
import { Reports } from "@/features/reports/Reports";
import { SessionsSection } from "@/features/sessions/SessionsSection";
import { useLesions } from "@/lib/lesions";
import { usePerson } from "@/lib/persons";
import { CalendarLink } from "./CalendarLink";
import { ProfilePage } from "./ProfilePage";

export type Tool = "appointments" | "sessions" | "reports" | "calendar" | "profile";

/** One of the person's tools as its own page under /persons/:id/{tool}. */
export function PersonToolPage({ tool }: { tool: Tool }) {
  const { personId = "" } = useParams();
  const { t } = useTranslation();
  const person = usePerson(personId);
  const lesions = useLesions(personId);
  if (person.error) return <Notice kind="error">{person.error.message}</Notice>;
  if (!person.data) return <p className="text-secondary">…</p>;
  const canEdit = person.data.my_role === "owner" || person.data.my_role === "manager";
  const data = person.data;
  switch (tool) {
    case "appointments":
      return <PrepareAppointment person={data} canEdit={canEdit} />;
    case "sessions":
      return <SessionsSection person={data} canEdit={canEdit} />;
    case "reports":
      return (
        <Reports
          person={data}
          titleOf={(id) => {
            const lesion = lesions.data?.find((item) => item.id === id);
            return lesion ? lesionTitle(lesion, t) : t("reports.deletedMark");
          }}
          marks={(lesions.data ?? []).map((lesion) => ({ id: lesion.id, title: lesionTitle(lesion, t) }))}
        />
      );
    case "calendar":
      return <CalendarLink person={data} />;
    case "profile":
      return <ProfilePage person={data} />;
  }
}
