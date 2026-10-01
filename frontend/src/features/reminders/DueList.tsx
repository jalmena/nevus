import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { zoneName } from "@/features/lesions/lesionName";
import { useDue } from "@/lib/reminders";
import styles from "./reminders.module.css";

/** Marks due for a photo across every person the user may see. Shown first on the home page. */
export function DueList() {
  const { t, i18n } = useTranslation();
  const due = useDue();
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium" });
  if (!due.data) return null;
  return (
    <section className={styles.due} aria-labelledby="due-heading">
      <h2 id="due-heading">{t("reminders.title")}</h2>
      {due.data.length === 0 ? (
        <p className="text-secondary">{t("reminders.nothing")}</p>
      ) : (
        <ul className={styles.list}>
          {due.data.map((item) => (
            <li key={item.lesion_id}>
              <Link to={`/lesions/${item.lesion_id}`} className={styles.item}>
                <span className={styles.title}>{item.label ?? zoneName(item.zone, t)}</span>
                <span className="text-secondary">
                  {item.person_name} ·{" "}
                  {item.overdue_days === 0
                    ? t("reminders.dueToday")
                    : t("reminders.dueSince", { date: dateFormat.format(new Date(item.next_due_on)) })}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
