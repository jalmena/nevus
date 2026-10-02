import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { formatBytes } from "@/lib/data";
import {
  useCreateReport,
  useDeleteReport,
  useReports,
  type Paper,
  type ReportLanguage,
  type ReportOut,
} from "@/lib/reports";
import styles from "./reports.module.css";

/**
 * Make a PDF for a clinician, and the list of those already made. On a mark's page it makes and lists
 * that mark's record; on a person's page, the summary of every mark and all the person's reports.
 */
export function Reports({
  personId,
  lesionId,
  titleOf,
}: {
  personId: string;
  lesionId?: string;
  /** The name of a mark, for listing its reports. */
  titleOf: (lesionId: string) => string;
}) {
  const { t, i18n } = useTranslation();
  const reports = useReports(personId);
  const create = useCreateReport(personId);
  const remove = useDeleteReport(personId);
  const uiLanguage: ReportLanguage = i18n.resolvedLanguage === "es" ? "es" : "en";
  const [language, setLanguage] = useState<ReportLanguage>(uiLanguage);
  const [paper, setPaper] = useState<Paper>("a4");
  const locale = i18n.resolvedLanguage ?? "en";
  const dateFormat = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" });
  const shown = (reports.data ?? []).filter((report) =>
    lesionId ? report.scope === "lesion" && report.lesion_ids.includes(lesionId) : true,
  );

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate(
      lesionId
        ? { scope: "lesion", lesion_id: lesionId, language, paper }
        : { scope: "profile", language, paper },
    );
  }

  function describe(report: ReportOut): string {
    if (report.scope === "profile") return t("reports.profile");
    const id = report.lesion_ids[0];
    return id ? t("reports.lesion", { name: titleOf(id) }) : t("reports.profile");
  }

  return (
    <section className={styles.section} aria-labelledby={lesionId ? "mark-reports" : "person-reports"}>
      <h2 id={lesionId ? "mark-reports" : "person-reports"}>{t("reports.title")}</h2>
      <p className="text-secondary">{lesionId ? t("reports.introLesion") : t("reports.introProfile")}</p>
      <form className={styles.form} onSubmit={submit}>
        <label className={styles.field}>
          <span>{t("reports.language")}</span>
          <select value={language} onChange={(e) => setLanguage(e.target.value as ReportLanguage)}>
            <option value="en">{t("languages.en")}</option>
            <option value="es">{t("languages.es")}</option>
          </select>
        </label>
        <label className={styles.field}>
          <span>{t("reports.paper")}</span>
          <select value={paper} onChange={(e) => setPaper(e.target.value as Paper)}>
            <option value="a4">A4</option>
            <option value="letter">{t("reports.letter")}</option>
          </select>
        </label>
        <Button type="submit" disabled={create.isPending}>
          {create.isPending
            ? t("common.working")
            : lesionId
              ? t("reports.makeLesion")
              : t("reports.makeProfile")}
        </Button>
      </form>
      {create.error && <Notice kind="error">{create.error.message}</Notice>}
      {shown.length > 0 && (
        <ul className={styles.list}>
          {shown.map((report) => (
            <li key={report.id} className={styles.item}>
              <span className={styles.what}>
                <span>{describe(report)}</span>
                <span className="text-secondary">
                  {dateFormat.format(new Date(report.created_at))} · {t(`languages.${report.language}`)} ·{" "}
                  {report.paper === "letter" ? t("reports.letter") : "A4"}
                </span>
                {report.status === "failed" && (
                  <span className={styles.failed}>{report.error ?? t("reports.failed")}</span>
                )}
              </span>
              <span className={styles.actions}>
                {report.status === "ready" && report.download_url ? (
                  <a href={report.download_url} download>
                    {t("reports.download", {
                      count: report.pages ?? 0,
                      size: formatBytes(report.bytes ?? 0, locale),
                    })}
                  </a>
                ) : report.status !== "failed" ? (
                  <span className="text-secondary" role="status">
                    {t("reports.making")}
                  </span>
                ) : null}
                {report.can_delete && (
                  <Button
                    variant="quiet"
                    onClick={() => remove.mutate(report.id)}
                    disabled={remove.isPending}
                    aria-label={t("reports.deleteNamed", { name: describe(report) })}
                  >
                    {t("reports.delete")}
                  </Button>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
