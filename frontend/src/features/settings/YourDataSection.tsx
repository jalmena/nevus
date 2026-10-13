import { Trash2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Row, RowList } from "@/design-system/components/Row";
import { ExportSheet } from "@/features/data/ExportForm";
import { ExportList } from "@/features/data/ExportList";
import { useExports, useTrash } from "@/lib/data";
import { SettingsHeader } from "./SettingsHeader";
import styles from "./settings.module.css";

/** The exports made, exporting the whole instance, and the way to the trash. */
export function YourDataSection({ admin }: { admin: boolean }) {
  const { t } = useTranslation();
  const trash = useTrash();
  const exports = useExports();
  const [exporting, setExporting] = useState(false);
  return (
    <div className={styles.page}>
      <SettingsHeader
        help={{
          title: t("data.title"),
          content: (
            <>
              <p>{t("data.hint")}</p>
              <p>{t("data.intro")}</p>
            </>
          ),
        }}
        admin={admin}
        title={t("data.title")}
        meta={[t("settings.status.exports", { count: exports.data?.length ?? 0 })]}
        primary={admin ? { label: t("data.exportAll"), onClick: () => setExporting(true) } : undefined}
      ></SettingsHeader>
      <ExportList />
      <RowList>
        <Row
          to="/trash"
          leading={<Trash2 />}
          title={t("trash.title")}
          meta={
            trash.data
              ? t("settings.status.exports", { count: trash.data.length, defaultValue: "" }) &&
                t("trash.keptFor")
              : undefined
          }
          chevron
        />
      </RowList>
      <ExportSheet
        personId={null}
        open={exporting}
        onClose={() => setExporting(false)}
        title={t("data.exportAll")}
      />
    </div>
  );
}
