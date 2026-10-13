import { useTranslation } from "react-i18next";
import { useParams } from "react-router";
import { Notice } from "@/design-system/components/Notice";
import { Reports } from "@/features/reports/Reports";
import { useLesion } from "@/lib/lesions";
import { usePerson } from "@/lib/persons";
import { lesionTitle } from "./lesionName";

/** The reports of one mark: its PDF record for the clinician. */
export function LesionReportsPage() {
  const { lesionId = "" } = useParams();
  const { t } = useTranslation();
  const lesion = useLesion(lesionId);
  const person = usePerson(lesion.data?.person_id ?? "");
  if (lesion.error) return <Notice kind="error">{lesion.error.message}</Notice>;
  if (!lesion.data || !person.data) return <p className="text-secondary">…</p>;
  const data = lesion.data;
  return <Reports person={person.data} lesion={data} titleOf={() => lesionTitle(data, t)} />;
}
