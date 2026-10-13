import { Clock } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Row, RowList, Thumb } from "@/design-system/components/Row";
import { StatusChip } from "@/design-system/components/StatusChip";
import { shortDate } from "@/lib/dates";
import { imageUrl } from "@/lib/images";
import type { LesionOut } from "@/lib/lesions";
import { lesionTitle, zoneName } from "./lesionName";

/** The Due chip, or the status word of a mark that is no longer active; nothing for the rest. */
export function DueBadge({ lesion }: { lesion: LesionOut }) {
  const { t } = useTranslation();
  if (lesion.status !== "active") return <StatusChip>{t(`lesions.statuses.${lesion.status}`)}</StatusChip>;
  if (lesion.due)
    return (
      <StatusChip kind="due" icon={<Clock />}>
        {t("lesions.dueNow")}
      </StatusChip>
    );
  return null;
}

/** The marks of a person as rows: thumbnail, name, zone and last visit, the Due chip or the next check. */
export function LesionList({ lesions }: { lesions: LesionOut[] }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage;
  return (
    <RowList>
      {lesions.map((lesion) => (
        <Row
          key={lesion.id}
          to={`/lesions/${lesion.id}`}
          leading={<Thumb src={lesion.latest_image_id ? imageUrl(lesion.latest_image_id, "thumb") : null} />}
          title={lesionTitle(lesion, t)}
          meta={[
            zoneName(lesion.location.zone, t),
            lesion.last_observed_at
              ? t("lesions.lastVisit", { date: shortDate(locale, lesion.last_observed_at) })
              : t("lesions.noVisits"),
            !lesion.due && lesion.status === "active" && lesion.next_due_on
              ? t("lesions.nextCheck", { date: shortDate(locale, lesion.next_due_on) })
              : null,
          ]
            .filter(Boolean)
            .join(" · ")}
          trailing={lesion.due || lesion.status !== "active" ? <DueBadge lesion={lesion} /> : undefined}
        />
      ))}
    </RowList>
  );
}
