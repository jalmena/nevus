import { TriangleAlert } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { shortDate } from "@/lib/dates";
import { thumbOf } from "@/lib/images";
import type { ObservationOut } from "@/lib/lesions";
import { formatMm, useLesionMeasurements } from "@/lib/measurements";
import styles from "./lesions.module.css";

/**
 * The visits of a mark, newest first, on a time rail: a point per visit with its date and the size
 * measured that day, its photographs and what was noted; a tick on the rail where the year changes.
 * The sizes are the series the size chart beside it loads (one per visit), so the rail asks for nothing.
 */
export function VisitTimeline({
  lesionId,
  visits,
  showUncertainty,
}: {
  lesionId: string;
  visits: ObservationOut[];
  showUncertainty: boolean;
}) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "en";
  const measurements = useLesionMeasurements(lesionId);
  const sizes = new Map((measurements.data ?? []).map((size) => [size.observation_id, size]));
  return (
    <ol className={styles.timeline}>
      {visits.map((visit, index) => {
        const year = visit.captured_local_date.slice(0, 4);
        const newYear = index > 0 && visits[index - 1]?.captured_local_date.slice(0, 4) !== year;
        const size = sizes.get(visit.id);
        return (
          <li
            key={visit.id}
            className={[styles.visit, index === 0 ? styles.latest : "", newYear ? styles.withYear : ""].join(
              " ",
            )}
          >
            {newYear && (
              <span className={styles.year} aria-hidden="true">
                {year}
              </span>
            )}
            <Link to={`/observations/${visit.id}`} className={styles.visitLink}>
              <span className={styles.visitHead}>
                <span className="numeric">{shortDate(locale, visit.captured_local_date)}</span>
                {size && <span className={styles.leader} aria-hidden="true" />}
                {size && (
                  <span className={[styles.visitSize, "numeric"].join(" ")}>
                    {formatMm(size.longest_mm, size.sigma_longest_mm, locale, showUncertainty)}
                  </span>
                )}
              </span>
              {visit.images.length > 0 && (
                <span className={styles.visitThumbs}>
                  {visit.images.slice(0, 4).map((image) => (
                    <img key={image.id} src={thumbOf(image)} alt="" width={56} height={56} loading="lazy" />
                  ))}
                </span>
              )}
              {visit.notes && <span className={styles.visitNotes}>{visit.notes}</span>}
              <span className={styles.visitMeta}>
                {[
                  t("observations.photoCount", { count: visit.images.length }),
                  ...visit.symptoms.map((symptom) => t(`observations.symptoms.${symptom}`)),
                ].join(" · ")}
                {visit.quality_flags.length > 0 && (
                  <span className={styles.qualityMeta}>
                    <TriangleAlert aria-hidden="true" /> {t("quality.short")}
                  </span>
                )}
              </span>
            </Link>
          </li>
        );
      })}
    </ol>
  );
}
