import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { imageUrl } from "@/lib/images";
import { daysUntil, type LesionOut } from "@/lib/lesions";
import { lesionTitle, locationLine } from "./lesionName";
import styles from "./lesions.module.css";

export function DueBadge({ lesion }: { lesion: LesionOut }) {
  const { t } = useTranslation();
  if (lesion.status !== "active")
    return <span className={styles.badge}>{t(`lesions.statuses.${lesion.status}`)}</span>;
  if (!lesion.next_due_on) return null;
  const days = daysUntil(lesion.next_due_on);
  if (lesion.due) return <span className={[styles.badge, styles.due].join(" ")}>{t("lesions.dueNow")}</span>;
  return <span className={styles.badge}>{t("lesions.dueIn", { count: days })}</span>;
}

export function LesionList({ lesions }: { lesions: LesionOut[] }) {
  const { t, i18n } = useTranslation();
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium" });
  return (
    <ul className={styles.list}>
      {lesions.map((lesion) => (
        <li key={lesion.id}>
          <Link to={`/lesions/${lesion.id}`} className={styles.item}>
            {lesion.latest_image_id ? (
              <img src={imageUrl(lesion.latest_image_id, "thumb")} alt="" className={styles.itemThumb} />
            ) : (
              <span className={styles.itemThumb} aria-hidden="true" />
            )}
            <span>
              <span className={styles.itemTitle}>{lesionTitle(lesion, t)}</span>
              <br />
              <span className="text-secondary">
                {locationLine(lesion, t)} ·{" "}
                {lesion.last_observed_at
                  ? t("lesions.lastVisit", { date: dateFormat.format(new Date(lesion.last_observed_at)) })
                  : t("lesions.noVisits")}
              </span>
            </span>
            <DueBadge lesion={lesion} />
          </Link>
        </li>
      ))}
    </ul>
  );
}
