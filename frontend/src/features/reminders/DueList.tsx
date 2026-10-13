import { Clock } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Row, RowList } from "@/design-system/components/Row";
import { StatusChip } from "@/design-system/components/StatusChip";
import { zoneName } from "@/features/lesions/lesionName";
import { shortDate } from "@/lib/dates";
import { useDue } from "@/lib/reminders";

/** Marks due for a photo across every person the user may see, as rows: the first list on the home page. */
export function DueRows() {
  const { t, i18n } = useTranslation();
  const due = useDue();
  if (!due.data || due.data.length === 0) return null;
  return (
    <RowList>
      {due.data.map((item) => (
        <Row
          key={item.lesion_id}
          to={`/lesions/${item.lesion_id}`}
          title={item.label ?? zoneName(item.zone, t)}
          meta={`${item.person_name} · ${
            item.overdue_days === 0
              ? t("reminders.dueToday")
              : t("reminders.dueSince", { date: shortDate(i18n.resolvedLanguage, item.next_due_on) })
          }`}
          trailing={
            <StatusChip kind="due" icon={<Clock />}>
              {t("lesions.dueNow")}
            </StatusChip>
          }
        />
      ))}
    </RowList>
  );
}
