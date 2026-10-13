import { Download, Trash2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { EmptyState } from "@/design-system/components/EmptyState";
import { IconButton } from "@/design-system/components/IconButton";
import { Notice } from "@/design-system/components/Notice";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Row, RowList } from "@/design-system/components/Row";
import { Select } from "@/design-system/components/Select";
import { Sheet } from "@/design-system/components/Sheet";
import { personRail } from "@/features/persons/personRail";
import { shortDateTime } from "@/lib/dates";
import { formatBytes } from "@/lib/data";
import type { LesionOut } from "@/lib/lesions";
import type { PersonOut } from "@/lib/persons";
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
 * The PDFs for a clinician as a page: the ones made, as rows, and making one in a sheet. Under a
 * person it offers the summary of every mark or the records of some; under a mark, that mark's record.
 */
export function Reports({
  person,
  lesion,
  titleOf,
  marks = [],
}: {
  person: PersonOut;
  lesion?: LesionOut;
  /** The name of a mark, for listing its reports. */
  titleOf: (lesionId: string) => string;
  /** On a person's page: the marks that can be chosen for a report of some of them. */
  marks?: { id: string; title: string }[];
}) {
  const { t, i18n } = useTranslation();
  const lesionId = lesion?.id;
  const reports = useReports(person.id);
  const create = useCreateReport(person.id);
  const remove = useDeleteReport(person.id);
  const uiLanguage: ReportLanguage = i18n.resolvedLanguage === "es" ? "es" : "en";
  const [open, setOpen] = useState(false);
  const [language, setLanguage] = useState<ReportLanguage>(uiLanguage);
  const [paper, setPaper] = useState<Paper>("a4");
  const [scope, setScope] = useState<"profile" | "selection">("profile");
  const [chosen, setChosen] = useState<string[]>([]);
  const locale = i18n.resolvedLanguage ?? "en";
  const shown = (reports.data ?? []).filter((report) =>
    lesionId ? report.scope === "lesion" && report.lesion_ids.includes(lesionId) : true,
  );

  function submit(event: FormEvent) {
    event.preventDefault();
    const done = { onSuccess: () => setOpen(false) };
    if (lesionId) create.mutate({ scope: "lesion", lesion_id: lesionId, language, paper }, done);
    else if (scope === "selection")
      create.mutate({ scope: "selection", lesion_ids: chosen, language, paper }, done);
    else create.mutate({ scope: "profile", language, paper }, done);
  }

  function describe(report: ReportOut): string {
    if (report.scope === "profile") return t("reports.profile");
    if (report.scope === "selection") return t("reports.selection", { count: report.lesion_ids.length });
    if (report.scope === "visit") return t("reports.visit");
    const id = report.lesion_ids[0];
    return id ? t("reports.lesion", { name: titleOf(id) }) : t("reports.profile");
  }

  const back = lesion
    ? { to: `/lesions/${lesion.id}`, label: titleOf(lesion.id) }
    : { to: `/persons/${person.id}`, label: person.display_name };
  const makeLabel = lesionId
    ? t("reports.makeLesion")
    : scope === "selection"
      ? t("reports.makeSelection", { count: chosen.length })
      : t("reports.makeProfile");

  return (
    <div className={styles.page}>
      <PageHeader
        help={{
          title: t("reports.title"),
          content: (
            <>
              <p>{lesionId ? t("reports.hintLesion") : t("reports.hint")}</p>
              <p>{lesionId ? t("reports.introLesion") : t("reports.introProfile")}</p>
            </>
          ),
        }}
        back={back}
        title={t("reports.title")}
        meta={[
          lesion ? titleOf(lesion.id) : person.display_name,
          reports.data
            ? shown.length > 0
              ? t("reports.made", { count: shown.length })
              : t("reports.none")
            : null,
        ]}
        rail={personRail(t, person.id, person.display_name)}
        primary={{ label: t("reports.make"), onClick: () => setOpen(true) }}
      ></PageHeader>
      {reports.error && <Notice kind="error">{reports.error.message}</Notice>}
      {reports.data && shown.length === 0 && <EmptyState>{t("reports.empty")}</EmptyState>}
      {shown.length > 0 && (
        <RowList>
          {shown.map((report) => (
            <Row
              key={report.id}
              title={describe(report)}
              meta={
                <>
                  {shortDateTime(locale, report.created_at)} · {t(`languages.${report.language}`)} ·{" "}
                  {report.paper === "letter" ? t("reports.letter") : "A4"}
                  {report.status === "failed" && (
                    <span className={styles.failed}>{report.error ?? t("reports.failed")}</span>
                  )}
                  {report.status !== "ready" && report.status !== "failed" && (
                    <span role="status">{t("reports.making")}</span>
                  )}
                </>
              }
              trailing={
                <>
                  {report.status === "ready" && report.download_url && (
                    <a
                      href={report.download_url}
                      download
                      className={styles.iconLink}
                      aria-label={t("reports.download", {
                        count: report.pages ?? 0,
                        size: formatBytes(report.bytes ?? 0, locale),
                      })}
                      title={t("reports.download", {
                        count: report.pages ?? 0,
                        size: formatBytes(report.bytes ?? 0, locale),
                      })}
                    >
                      <Download aria-hidden="true" />
                    </a>
                  )}
                  {report.can_delete && (
                    <IconButton
                      label={t("reports.deleteNamed", { name: describe(report) })}
                      icon={<Trash2 />}
                      onClick={() => remove.mutate(report.id)}
                      disabled={remove.isPending}
                    />
                  )}
                </>
              }
            />
          ))}
        </RowList>
      )}
      <Sheet open={open} title={t("reports.make")} onClose={() => setOpen(false)}>
        <form className={styles.form} onSubmit={submit}>
          {!lesionId && marks.length > 0 && (
            <fieldset className={styles.choice}>
              <legend>{t("reports.what")}</legend>
              <label>
                <input
                  type="radio"
                  name="scope"
                  checked={scope === "profile"}
                  onChange={() => setScope("profile")}
                />
                {t("reports.whatProfile")}
              </label>
              <label>
                <input
                  type="radio"
                  name="scope"
                  checked={scope === "selection"}
                  onChange={() => setScope("selection")}
                />
                {t("reports.whatSelection")}
              </label>
              {scope === "selection" && (
                <ul className={styles.marks}>
                  {marks.map((mark) => (
                    <li key={mark.id}>
                      <label>
                        <input
                          type="checkbox"
                          checked={chosen.includes(mark.id)}
                          onChange={(e) =>
                            setChosen((current) =>
                              e.target.checked
                                ? [...current, mark.id]
                                : current.filter((id) => id !== mark.id),
                            )
                          }
                        />
                        {mark.title}
                      </label>
                    </li>
                  ))}
                </ul>
              )}
            </fieldset>
          )}
          <Select
            label={t("reports.language")}
            value={language}
            onChange={(e) => setLanguage(e.target.value as ReportLanguage)}
            options={[
              { value: "en", label: t("languages.en") },
              { value: "es", label: t("languages.es") },
            ]}
          />
          <Select
            label={t("reports.paper")}
            value={paper}
            onChange={(e) => setPaper(e.target.value as Paper)}
            options={[
              { value: "a4", label: "A4" },
              { value: "letter", label: t("reports.letter") },
            ]}
          />
          {create.error && <Notice kind="error">{create.error.message}</Notice>}
          <div className={styles.actions}>
            <Button type="button" variant="quiet" onClick={() => setOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              type="submit"
              disabled={create.isPending || (scope === "selection" && !lesionId && chosen.length === 0)}
            >
              {create.isPending ? t("common.working") : makeLabel}
            </Button>
          </div>
        </form>
      </Sheet>
    </div>
  );
}
