import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";
import { Notice } from "@/design-system/components/Notice";
import { ComparisonViewer } from "@/features/compare/ComparisonViewer";
import { useBodySession, useSessionPairs } from "@/lib/sessions";
import styles from "./sessions.module.css";

/** FR-SES-04: two sessions of the same person, zone by zone. */
export function SessionComparePage() {
  const { sessionId = "", otherId = "" } = useParams();
  const { t, i18n } = useTranslation();
  const pairs = useSessionPairs(sessionId, otherId);
  const one = useBodySession(sessionId);
  const two = useBodySession(otherId);
  const [chosen, setChosen] = useState<string | null>(null);
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium" });

  if (pairs.error) return <Notice kind="error">{pairs.error.message}</Notice>;
  if (!pairs.data || !one.data || !two.data) return <p className="text-secondary">…</p>;
  const [earlier, later] = [one.data, two.data].sort((a, b) => a.started_at.localeCompare(b.started_at));
  if (!earlier || !later) return null;
  const zone = chosen ?? pairs.data[0]?.zone ?? null;
  const pair = pairs.data.find((item) => item.zone === zone);
  const size = (session: typeof earlier, id: string) => {
    const found = session.zones.find((item) => item.image_id === id);
    return { width: found?.upright_width ?? 1, height: found?.upright_height ?? 1 };
  };

  return (
    <div className={styles.page}>
      <p>
        <Link to={`/sessions/${later.id}`}>{t("sessions.backToSession")}</Link>
      </p>
      <h1>{t("sessions.compareTitle")}</h1>
      <p className="text-secondary">
        {t("sessions.compareDates", {
          earlier: dateFormat.format(new Date(earlier.started_at)),
          later: dateFormat.format(new Date(later.started_at)),
        })}
      </p>
      {pairs.data.length === 0 ? (
        <Notice kind="info">{t("sessions.compareNone")}</Notice>
      ) : (
        <label className={styles.field}>
          <span>{t("sessions.compareZone")}</span>
          <select value={zone ?? ""} onChange={(e) => setChosen(e.target.value)}>
            {pairs.data.map((item) => (
              <option key={item.zone} value={item.zone}>
                {t(`sessions.zones.${item.zone}.name`)}
              </option>
            ))}
          </select>
        </label>
      )}
      {pair && (
        <ComparisonViewer
          key={pair.zone}
          a={{
            id: pair.earlier_image_id,
            ...size(earlier, pair.earlier_image_id),
            label: dateFormat.format(new Date(earlier.started_at)),
          }}
          b={{
            id: pair.later_image_id,
            ...size(later, pair.later_image_id),
            label: dateFormat.format(new Date(later.started_at)),
          }}
        />
      )}
    </div>
  );
}
