import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { formatBytes, useExports, useRemoveExport } from "@/lib/data";
import styles from "./data.module.css";

export function ExportList() {
  const { t, i18n } = useTranslation();
  const exports = useExports();
  const remove = useRemoveExport();
  const locale = i18n.resolvedLanguage ?? "en";
  const dateFormat = new Intl.DateTimeFormat(locale, { dateStyle: "medium" });
  if (!exports.data || exports.data.length === 0) return null;
  return (
    <ul className={styles.list}>
      {exports.data.map((item) => (
        <li key={item.id} className={styles.item}>
          <span>
            {item.status === "ready" && item.file_name ? (
              <a href={`/api/exports/${item.id}/download`} download>
                {item.file_name}
              </a>
            ) : (
              <span>{t(`data.status.${item.status}`, { defaultValue: item.status })}</span>
            )}
            <br />
            <span className="text-secondary">
              {item.bytes ? `${formatBytes(item.bytes, locale)} · ` : ""}
              {item.expires_at
                ? t("data.expires", { date: dateFormat.format(new Date(item.expires_at)) })
                : dateFormat.format(new Date(item.created_at))}
            </span>
          </span>
          <Button variant="quiet" onClick={() => remove.mutate(item.id)} disabled={remove.isPending}>
            {t("data.remove")}
          </Button>
        </li>
      ))}
    </ul>
  );
}
