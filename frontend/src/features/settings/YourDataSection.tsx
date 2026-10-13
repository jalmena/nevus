import { Trash2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Help } from "@/design-system/components/Help";
import { Row, RowList } from "@/design-system/components/Row";
import { ExportSheet } from "@/features/data/ExportForm";
import { ExportList } from "@/features/data/ExportList";
import { useTrash } from "@/lib/data";
import { SettingsHeader } from "./SettingsHeader";
import styles from "./settings.module.css";

/** The exports made, exporting the whole instance, and the way to the trash. */
export function YourDataSection({ admin }: { admin: boolean }) {
  const { t } = useTranslation();
  const trash = useTrash();
  const [exporting, setExporting] = useState(false);
  return (
    <div className={styles.page}>
      <SettingsHeader
        admin={admin}
        title={t("data.title")}
        primary={admin ? { label: t("data.exportAll"), onClick: () => setExporting(true) } : undefined}
      >
        <p className={["text-secondary", styles.intro].join(" ")}>
          {t("data.hint")}
          <Help title={t("data.title")} as="text">
            <p>{t("data.intro")}</p>
          </Help>
        </p>
      </SettingsHeader>
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
