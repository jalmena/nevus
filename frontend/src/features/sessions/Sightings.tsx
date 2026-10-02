import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { useSightings } from "@/lib/sessions";
import styles from "./sessions.module.css";

/** On a mark's page: where it was seen in full-body sessions. */
export function Sightings({ lesionId }: { lesionId: string }) {
  const { t, i18n } = useTranslation();
  const sightings = useSightings(lesionId);
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium" });
  if (!sightings.data || sightings.data.length === 0) return null;
  return (
    <section className={styles.section} aria-labelledby="sightings-heading">
      <h2 id="sightings-heading">{t("sessions.sightings")}</h2>
      <ul className={styles.marks}>
        {sightings.data.map((item) => (
          <li key={item.mark_id}>
            <Link to={`/sessions/${item.session_id}/zones/${item.zone}`} className={styles.markButton}>
              <img src={item.crop_url} alt="" />
              <span>
                {dateFormat.format(new Date(item.started_at))} · {t(`sessions.zones.${item.zone}.name`)}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
