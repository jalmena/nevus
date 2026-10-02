import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";
import { Button } from "@/design-system/components/Button";
import { FileButton } from "@/design-system/components/FileButton";
import { Notice } from "@/design-system/components/Notice";
import { imageUrl } from "@/lib/images";
import {
  useDeleteSession,
  useFinishSession,
  useProtocol,
  useBodySession,
  useSkipZone,
  useZonePhoto,
} from "@/lib/sessions";
import styles from "./sessions.module.css";

/** A full-body session: each region of the body in the protocol's order, photographed or skipped. */
export function SessionPage() {
  const { sessionId = "" } = useParams();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const protocol = useProtocol();
  const session = useBodySession(sessionId);
  const photo = useZonePhoto(sessionId);
  const skip = useSkipZone(sessionId);
  const finish = useFinishSession(sessionId);
  const remove = useDeleteSession();
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "long" });

  if (session.error) return <Notice kind="error">{session.error.message}</Notice>;
  if (!session.data || !protocol.data) return <p className="text-secondary">…</p>;
  const data = session.data;
  const sensitive = new Set(protocol.data.filter((zone) => zone.sensitive).map((zone) => zone.id));
  const captured = data.zones.filter((zone) => zone.status === "captured").length;
  const current = data.zones.find((zone) => zone.status === "pending")?.zone;
  const busy = photo.isPending || skip.isPending;

  return (
    <div className={styles.page}>
      <p>
        <Link to={`/persons/${data.person_id}`}>{t("sessions.back")}</Link>
      </p>
      <h1>{t("sessions.titleFor", { date: dateFormat.format(new Date(data.started_at)) })}</h1>
      <p className="text-secondary">
        {data.status === "open" ? t("sessions.open") : t("sessions.finished")} ·{" "}
        {t("sessions.progress", { captured, total: data.zones.length })}
      </p>
      <p className="text-secondary">{t("sessions.howTo")}</p>
      {data.experimental && <Notice kind="info">{t("sessions.experimentalNote")}</Notice>}
      {(photo.error ?? skip.error) && <Notice kind="error">{(photo.error ?? skip.error)?.message}</Notice>}
      <ol className={styles.zones}>
        {data.zones.map((zone) => (
          <li
            key={zone.zone}
            className={[styles.zone, styles[zone.status], zone.zone === current ? styles.current : ""].join(
              " ",
            )}
          >
            <div className={styles.zoneText}>
              <h2>{t(`sessions.zones.${zone.zone}.name`)}</h2>
              {zone.status === "pending" && zone.zone === current && (
                <>
                  <p className="text-secondary">{t(`sessions.zones.${zone.zone}.pose`)}</p>
                  {sensitive.has(zone.zone) && <p className="text-secondary">{t("sessions.sensitive")}</p>}
                </>
              )}
              {zone.status === "pending" && zone.zone !== current && (
                <details className={styles.pose}>
                  <summary>{t("sessions.pose")}</summary>
                  <p className="text-secondary">{t(`sessions.zones.${zone.zone}.pose`)}</p>
                  {sensitive.has(zone.zone) && <p className="text-secondary">{t("sessions.sensitive")}</p>}
                </details>
              )}
              <p className={styles.status} role={zone.analysing ? "status" : undefined}>
                {zone.analysing
                  ? t("sessions.analysing")
                  : zone.status === "captured"
                    ? t("sessions.marksCount", {
                        count: zone.marks.filter((m) => m.state === "confirmed").length,
                      })
                    : zone.status === "skipped"
                      ? t("sessions.skipped")
                      : t("sessions.pending")}
              </p>
            </div>
            {zone.image_id && (
              <Link to={`/sessions/${data.id}/zones/${zone.zone}`} className={styles.thumb}>
                <img
                  src={imageUrl(zone.image_id, "thumb")}
                  alt={t("sessions.openZone", { zone: t(`sessions.zones.${zone.zone}.name`) })}
                />
              </Link>
            )}
            {data.can_edit && (
              <div className={styles.actions}>
                {zone.status !== "skipped" && (
                  <FileButton
                    label={zone.status === "captured" ? t("sessions.retake") : t("sessions.takePhoto")}
                    variant={zone.status === "pending" && zone.zone === current ? "primary" : "secondary"}
                    capture="environment"
                    disabled={busy}
                    onFiles={(files) => files[0] && photo.mutate({ zone: zone.zone, file: files[0] })}
                  />
                )}
                {zone.status === "pending" && (
                  <Button
                    variant="quiet"
                    onClick={() => skip.mutate({ zone: zone.zone, skip: true })}
                    disabled={busy}
                  >
                    {t("sessions.skip")}
                  </Button>
                )}
                {zone.status === "skipped" && (
                  <Button
                    variant="quiet"
                    onClick={() => skip.mutate({ zone: zone.zone, skip: false })}
                    disabled={busy}
                  >
                    {t("sessions.unskip")}
                  </Button>
                )}
              </div>
            )}
          </li>
        ))}
      </ol>
      {data.can_edit && (
        <div className={styles.actions}>
          {data.status === "open" && (
            <Button onClick={() => finish.mutate()} disabled={finish.isPending}>
              {t("sessions.finish")}
            </Button>
          )}
          <Button
            variant="quiet"
            onClick={() => {
              if (window.confirm(t("sessions.deleteConfirm")))
                remove.mutate(data.id, { onSuccess: () => void navigate(`/persons/${data.person_id}`) });
            }}
            disabled={remove.isPending}
          >
            {t("sessions.delete")}
          </Button>
        </div>
      )}
    </div>
  );
}
