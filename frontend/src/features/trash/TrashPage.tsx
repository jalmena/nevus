import { Camera, CircleDot, Image, PersonStanding, RotateCcw, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { EmptyState } from "@/design-system/components/EmptyState";
import { IconButton } from "@/design-system/components/IconButton";
import { Notice } from "@/design-system/components/Notice";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Row, RowList } from "@/design-system/components/Row";
import { useConfirm } from "@/lib/confirm/ConfirmProvider";
import { usePurgeNow, useRestore, useTrash } from "@/lib/data";
import styles from "./trash.module.css";

const ICONS = { person: PersonStanding, lesion: CircleDot, observation: Camera, image: Image } as const;

/** What was deleted in the last 30 days: restore it, or let it go now. */
export function TrashPage() {
  const { t, i18n } = useTranslation();
  const confirm = useConfirm();
  const trash = useTrash();
  const restore = useRestore();
  const purge = usePurgeNow();
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium" });
  return (
    <div className={styles.page}>
      <PageHeader
        back={{ to: "/settings/your-data", label: t("settings.title") }}
        title={t("trash.title")}
        meta={[t("trash.keptFor")]}
      />
      {trash.error && <Notice kind="error">{trash.error.message}</Notice>}
      {trash.data && trash.data.length === 0 && <EmptyState>{t("trash.emptyText")}</EmptyState>}
      {trash.data && trash.data.length > 0 && (
        <RowList>
          {trash.data.map((item) => {
            const Icon = ICONS[item.kind as keyof typeof ICONS] ?? Image;
            return (
              <Row
                key={`${item.kind}-${item.id}`}
                leading={<Icon />}
                title={item.label}
                meta={`${t(`trash.kinds.${item.kind}`)} · ${item.person_name} · ${t("trash.goesOn", {
                  date: dateFormat.format(new Date(item.purge_after)),
                })}`}
                trailing={
                  <>
                    <IconButton
                      label={t("trash.restore")}
                      icon={<RotateCcw />}
                      showLabel="desktop"
                      onClick={() => restore.mutate({ kind: item.kind, id: item.id })}
                      disabled={restore.isPending}
                    />
                    <IconButton
                      label={t("trash.deleteNow")}
                      icon={<Trash2 />}
                      disabled={purge.isPending}
                      onClick={() => {
                        void confirm({
                          title: t("trash.deleteNowQuestion"),
                          text: t("trash.deleteNowNote"),
                          action: t("trash.deleteNow"),
                          danger: true,
                        }).then((yes) => yes && purge.mutate({ kind: item.kind, id: item.id }));
                      }}
                    />
                  </>
                }
              />
            );
          })}
        </RowList>
      )}
      {(restore.error ?? purge.error) && (
        <Notice kind="error">{(restore.error ?? purge.error)?.message}</Notice>
      )}
    </div>
  );
}
