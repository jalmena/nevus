import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { Notice } from "@/design-system/components/Notice";
import { Segmented } from "@/design-system/components/Segmented";
import { zoneName } from "@/features/lesions/lesionName";
import { useEvaluationPhotos, useEvaluationSummary, type OutlineRow } from "@/lib/evaluation";
import { imageUrl } from "@/lib/images";
import styles from "./evaluation.module.css";

const FILTERS = ["unlabelled", "labelled", "all"] as const;

/** For administrators: label their own photos to see how the analyzers do, per skin tone (FR-ANA-05). */
export function EvaluationPage() {
  const { t, i18n } = useTranslation();
  const [only, setOnly] = useState<(typeof FILTERS)[number]>("unlabelled");
  const photos = useEvaluationPhotos(only);
  const summary = useEvaluationSummary();
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium" });
  const percent = new Intl.NumberFormat(i18n.resolvedLanguage, {
    style: "percent",
    maximumFractionDigits: 1,
  });
  const number = new Intl.NumberFormat(i18n.resolvedLanguage, { maximumFractionDigits: 2 });
  const cell = (value: number | null, asPercent = false) =>
    value === null ? "—" : asPercent ? percent.format(value) : number.format(value);

  const rows: [string, OutlineRow][] = summary.data
    ? [...Object.entries(summary.data.outline.by_tone), [t("evaluation.all"), summary.data.outline.overall]]
    : [];

  return (
    <div className={styles.page}>
      <p>
        <Link to="/settings">{t("evaluation.back")}</Link>
      </p>
      <h1>{t("evaluation.title")}</h1>
      <p className="text-secondary">{t("evaluation.intro")}</p>

      <section className={styles.section} aria-labelledby="summary-heading">
        <h2 id="summary-heading">{t("evaluation.summary")}</h2>
        {summary.data && summary.data.labelled === 0 ? (
          <p className="text-secondary">{t("evaluation.nothingYet")}</p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <caption className="text-secondary">
                {t("evaluation.caption", {
                  name: summary.data?.analyzer.name ?? "",
                  version: summary.data?.analyzer.version ?? "",
                })}
              </caption>
              <thead>
                <tr>
                  <th scope="col">{t("evaluation.tone")}</th>
                  <th scope="col">{t("evaluation.photos")}</th>
                  <th scope="col">{t("evaluation.found")}</th>
                  <th scope="col">IoU</th>
                  <th scope="col">Dice</th>
                  <th scope="col">{t("evaluation.diameterError")}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(([tone, row]) => (
                  <tr key={tone}>
                    <th scope="row">{tone === "unknown" ? t("evaluation.unknownTone") : tone}</th>
                    <td className="numeric">{row.photos}</td>
                    <td className="numeric">{row.found}</td>
                    <td className="numeric">{cell(row.mean_iou)}</td>
                    <td className="numeric">{cell(row.mean_dice)}</td>
                    <td className="numeric">
                      {cell(row.mean_diameter_error, true)} / {cell(row.worst_diameter_error, true)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {summary.data && summary.data.quality.overall.photos > 0 && (
          <p>
            {t("evaluation.quality", {
              agreement: cell(summary.data.quality.overall.agreement, true),
              caught: summary.data.quality.overall.poor_caught,
              poor: summary.data.quality.overall.poor_caught + summary.data.quality.overall.poor_missed,
              flagged: summary.data.quality.overall.good_flagged,
              good: summary.data.quality.overall.good_flagged + summary.data.quality.overall.good_clear,
            })}
          </p>
        )}
        <p className="text-secondary">{t("evaluation.command")}</p>
      </section>

      <section className={styles.section} aria-labelledby="photos-heading">
        <h2 id="photos-heading">{t("evaluation.photosTitle")}</h2>
        <Segmented
          label={t("evaluation.filter")}
          options={FILTERS.map((value) => ({ value, label: t(`evaluation.filters.${value}`) }))}
          value={only}
          onChange={setOnly}
        />
        {photos.error && <Notice kind="error">{photos.error.message}</Notice>}
        {photos.data && photos.data.length === 0 && <p className="text-secondary">{t("evaluation.none")}</p>}
        <ul className={styles.grid}>
          {photos.data?.map((photo) => (
            <li key={photo.image_id}>
              <Link to={`/evaluation/${photo.image_id}`} className={styles.photo}>
                <img src={imageUrl(photo.image_id, "thumb")} alt="" loading="lazy" />
                <span>
                  {photo.person_name} · {photo.mark === photo.zone ? zoneName(photo.zone, t) : photo.mark}
                </span>
                <span className="text-secondary">
                  {photo.captured_on ? dateFormat.format(new Date(`${photo.captured_on}T12:00:00`)) : ""}
                  {photo.label ? ` · ${t("evaluation.labelled")}` : ""}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
