import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { Button } from "@/design-system/components/Button";
import { EmptyState } from "@/design-system/components/EmptyState";
import { Notice } from "@/design-system/components/Notice";
import { usePurgeNow, useRestore, useTrash } from "@/lib/data";
import styles from "./trash.module.css";

export function TrashPage() {
  const { t, i18n } = useTranslation();
  const trash = useTrash();
  const restore = useRestore();
  const purge = usePurgeNow();
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium" });
  return (
    <div className={styles.page}>
      <p>
        <Link to="/settings">{t("trash.backToSettings")}</Link>
      </p>
      <h1>{t("trash.title")}</h1>
      <p className="text-secondary">{t("trash.intro")}</p>
      {trash.error && <Notice kind="error">{trash.error.message}</Notice>}
      {trash.data && trash.data.length === 0 && (
        <EmptyState title={t("trash.emptyTitle")} text={t("trash.emptyText")} />
      )}
      <ul className={styles.list}>
        {trash.data?.map((item) => (
          <li key={`${item.kind}-${item.id}`} className={styles.item}>
            <span>
              <strong>{item.label}</strong>
              <br />
              <span className="text-secondary">
                {t(`trash.kinds.${item.kind}`)} · {item.person_name} ·{" "}
                {t("trash.goesOn", { date: dateFormat.format(new Date(item.purge_after)) })}
              </span>
            </span>
            <span className={styles.actions}>
              <Button
                variant="secondary"
                onClick={() => restore.mutate({ kind: item.kind, id: item.id })}
                disabled={restore.isPending}
              >
                {t("trash.restore")}
              </Button>
              <Button
                variant="danger"
                onClick={() => purge.mutate({ kind: item.kind, id: item.id })}
                disabled={purge.isPending}
              >
                {t("trash.deleteNow")}
              </Button>
            </span>
          </li>
        ))}
      </ul>
      {(restore.error ?? purge.error) && (
        <Notice kind="error">{(restore.error ?? purge.error)?.message}</Notice>
      )}
    </div>
  );
}
