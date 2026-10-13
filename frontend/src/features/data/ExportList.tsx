import { Download, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { IconButton } from "@/design-system/components/IconButton";
import { Row, RowList } from "@/design-system/components/Row";
import { formatBytes, useExports, useRemoveExport } from "@/lib/data";
import styles from "./data.module.css";

/** The exports made: a download while they last, and a way to remove them. */
export function ExportList() {
  const { t, i18n } = useTranslation();
  const exports = useExports();
  const remove = useRemoveExport();
  const locale = i18n.resolvedLanguage ?? "en";
  const dateFormat = new Intl.DateTimeFormat(locale, { dateStyle: "medium" });
  if (!exports.data || exports.data.length === 0) return null;
  return (
    <RowList>
      {exports.data.map((item) => (
        <Row
          key={item.id}
          title={item.file_name ?? t(`data.status.${item.status}`, { defaultValue: item.status })}
          meta={[
            item.status !== "ready" ? t(`data.status.${item.status}`, { defaultValue: item.status }) : null,
            item.bytes ? formatBytes(item.bytes, locale) : null,
            item.expires_at
              ? t("data.expires", { date: dateFormat.format(new Date(item.expires_at)) })
              : dateFormat.format(new Date(item.created_at)),
          ]
            .filter(Boolean)
            .join(" · ")}
          trailing={
            <>
              {item.status === "ready" && item.file_name && (
                <a
                  href={`/api/exports/${item.id}/download`}
                  download
                  className={styles.iconLink}
                  aria-label={item.file_name}
                  title={item.file_name}
                >
                  <Download aria-hidden="true" />
                </a>
              )}
              <IconButton
                label={t("data.remove")}
                icon={<Trash2 />}
                onClick={() => remove.mutate(item.id)}
                disabled={remove.isPending}
              />
            </>
          }
        />
      ))}
    </RowList>
  );
}
