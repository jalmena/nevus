import { Check, Circle, CircleDashed, Trash2 } from "lucide-react";
import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";
import { EmptyState } from "@/design-system/components/EmptyState";
import { Notice } from "@/design-system/components/Notice";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Row, RowList, Thumb } from "@/design-system/components/Row";
import { StatusChip } from "@/design-system/components/StatusChip";
import { useConfirm } from "@/lib/confirm/ConfirmProvider";
import { imageUrl } from "@/lib/images";
import {
  useBodySession,
  useDeleteSession,
  useFinishSession,
  useProtocol,
  useSkipZone,
  useZonePhoto,
} from "@/lib/sessions";
import styles from "./sessions.module.css";

/** A full-body session: the region to photograph next, and every region in the protocol's order. */
export function SessionPage() {
  const { sessionId = "" } = useParams();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const confirm = useConfirm();
  const protocol = useProtocol();
  const session = useBodySession(sessionId);
  const photo = useZonePhoto(sessionId);
  const skip = useSkipZone(sessionId);
  const finish = useFinishSession(sessionId);
  const remove = useDeleteSession();
  const camera = useRef<HTMLInputElement>(null);
  const [chosen, setChosen] = useState<string | null>(null);
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "long" });

  if (session.error) return <Notice kind="error">{session.error.message}</Notice>;
  if (!session.data || !protocol.data) return <p className="text-secondary">…</p>;
  const data = session.data;
  const sensitive = new Set(protocol.data.filter((zone) => zone.sensitive).map((zone) => zone.id));
  const captured = data.zones.filter((zone) => zone.status === "captured").length;
  const skipped = data.zones.filter((zone) => zone.status === "skipped").length;
  const total = data.zones.length;
  const current =
    data.zones.find((zone) => zone.zone === chosen && zone.status === "pending") ??
    data.zones.find((zone) => zone.status === "pending");
  const busy = photo.isPending || skip.isPending;
  const canEdit = data.can_edit && data.status === "open";
  const name = (zone: string) => t(`sessions.zones.${zone}.name`);

  return (
    <div className={[styles.page, "page-wide"].join(" ")}>
      <PageHeader
        back={{ to: `/persons/${data.person_id}/sessions`, label: t("sessions.title") }}
        title={t("sessions.titleFor", { date: dateFormat.format(new Date(data.started_at)) })}
        meta={[
          data.status === "open" ? t("sessions.open") : t("sessions.finished"),
          t("sessions.progress", { captured, total }),
          skipped > 0 ? t("sessions.skippedCount", { count: skipped }) : null,
        ]}
        chip={
          data.experimental ? (
            <StatusChip kind="experimental">{t("proposals.experimental")}</StatusChip>
          ) : undefined
        }
        help={{
          title: t("sessions.tips"),
          content: (
            <>
              <p>{t("sessions.howToMore")}</p>
              {data.experimental && <p>{t("sessions.experimentalNote")}</p>}
            </>
          ),
        }}
        primary={
          canEdit && current
            ? { label: t("sessions.takePhoto"), pending: busy, onClick: () => camera.current?.click() }
            : undefined
        }
        secondary={
          canEdit && current
            ? { label: t("sessions.skip"), onClick: () => skip.mutate({ zone: current.zone, skip: true }) }
            : undefined
        }
        menu={
          data.can_edit
            ? [
                ...(data.status === "open"
                  ? [
                      {
                        label: t("sessions.finish"),
                        icon: <Check />,
                        disabled: finish.isPending,
                        onSelect: () => finish.mutate(),
                      },
                    ]
                  : []),
                {
                  label: t("sessions.delete"),
                  icon: <Trash2 />,
                  danger: true,
                  onSelect: () => {
                    void confirm({
                      title: t("sessions.deleteQuestion"),
                      text: t("sessions.deleteNote"),
                      action: t("sessions.delete"),
                      danger: true,
                    }).then(
                      (yes) =>
                        yes &&
                        remove.mutate(data.id, {
                          onSuccess: () => void navigate(`/persons/${data.person_id}`),
                        }),
                    );
                  },
                },
              ]
            : []
        }
      >
        <div
          className={styles.progress}
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={total}
          aria-valuenow={captured}
          aria-label={t("sessions.progress", { captured, total })}
        >
          <span style={{ width: `${total ? (captured / total) * 100 : 0}%` }} />
        </div>
        <p className={["text-secondary", styles.howTo].join(" ")}>{t("sessions.howTo")}</p>
      </PageHeader>
      {(photo.error ?? skip.error ?? finish.error ?? remove.error) && (
        <Notice kind="error">{(photo.error ?? skip.error ?? finish.error ?? remove.error)?.message}</Notice>
      )}
      {canEdit && (
        <input
          ref={camera}
          type="file"
          accept="image/*"
          capture="environment"
          className={styles.hiddenInput}
          aria-label={t("sessions.takePhoto")}
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (file && current) photo.mutate({ zone: current.zone, file });
          }}
        />
      )}

      <div className={styles.layout}>
        <div className={styles.regionPane}>
          {current ? (
            <article
              className={styles.current}
              aria-label={t("sessions.selectRegion", { zone: name(current.zone) })}
            >
              <h2>{name(current.zone)}</h2>
              <p>{t(`sessions.zones.${current.zone}.pose`)}</p>
              {sensitive.has(current.zone) && <p className="text-secondary">{t("sessions.sensitive")}</p>}
            </article>
          ) : (
            data.status === "open" && <EmptyState>{t("sessions.allDone")}</EmptyState>
          )}
        </div>
        <RowList className={styles.regions} label={t("sessions.title")}>
          {data.zones.map((zone) => {
            const isCurrent = zone.zone === current?.zone;
            const meta = zone.analysing
              ? t("sessions.analysing")
              : zone.status === "captured"
                ? t("sessions.marksCount", {
                    count: zone.marks.filter((m) => m.state === "confirmed").length,
                  })
                : zone.status === "skipped"
                  ? t("sessions.skipped")
                  : t("sessions.notYet");
            if (zone.status === "captured" && zone.image_id)
              return (
                <Row
                  key={zone.zone}
                  to={`/sessions/${data.id}/zones/${zone.zone}`}
                  leading={<Thumb src={imageUrl(zone.image_id, "thumb")} />}
                  title={name(zone.zone)}
                  meta={<span role={zone.analysing ? "status" : undefined}>{meta}</span>}
                />
              );
            return (
              <Row
                key={zone.zone}
                onClick={
                  canEdit
                    ? () => {
                        setChosen(zone.zone);
                        if (zone.status === "skipped") skip.mutate({ zone: zone.zone, skip: false });
                      }
                    : undefined
                }
                selected={isCurrent}
                leading={zone.status === "skipped" ? <CircleDashed /> : <Circle />}
                title={name(zone.zone)}
                meta={meta}
              />
            );
          })}
        </RowList>
      </div>
    </div>
  );
}
