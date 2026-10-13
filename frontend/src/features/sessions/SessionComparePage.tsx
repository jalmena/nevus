import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";
import { Notice } from "@/design-system/components/Notice";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Select } from "@/design-system/components/Select";
import { ComparisonViewer } from "@/features/compare/ComparisonViewer";
import { personRail } from "@/features/persons/personRail";
import { shortDate } from "@/lib/dates";
import { usePerson } from "@/lib/persons";
import { useBodySession, useSessionPairs } from "@/lib/sessions";
import styles from "./sessions.module.css";

/** FR-SES-04: two sessions of the same person, zone by zone. */
export function SessionComparePage() {
  const { sessionId = "", otherId = "" } = useParams();
  const { t, i18n } = useTranslation();
  const pairs = useSessionPairs(sessionId, otherId);
  const one = useBodySession(sessionId);
  const two = useBodySession(otherId);
  const person = usePerson(one.data?.person_id ?? "");
  const [chosen, setChosen] = useState<string | null>(null);
  const locale = i18n.resolvedLanguage;

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
    <div className={[styles.page, "page-wide"].join(" ")}>
      <PageHeader
        back={{
          to: `/sessions/${later.id}`,
          label: t("sessions.titleFor", { date: shortDate(locale, later.started_at) }),
        }}
        title={t("sessions.compareTitle")}
        rail={personRail(t, later.person_id, person.data?.display_name)}
        meta={[
          t("sessions.compareDates", {
            earlier: shortDate(locale, earlier.started_at),
            later: shortDate(locale, later.started_at),
          }),
        ]}
        help={{ title: t("common.help"), content: <p>{t("compare.zoomHint")}</p> }}
      />
      {pairs.data.length === 0 ? (
        <Notice kind="info">{t("sessions.compareNone")}</Notice>
      ) : (
        <Select
          label={t("sessions.compareZone")}
          value={zone ?? ""}
          onChange={(e) => setChosen(e.target.value)}
          options={pairs.data.map((item) => ({
            value: item.zone,
            label: t(`sessions.zones.${item.zone}.name`),
          }))}
        />
      )}
      {pair && (
        <ComparisonViewer
          key={pair.zone}
          a={{
            id: pair.earlier_image_id,
            ...size(earlier, pair.earlier_image_id),
            label: shortDate(locale, earlier.started_at),
          }}
          b={{
            id: pair.later_image_id,
            ...size(later, pair.later_image_id),
            label: shortDate(locale, later.started_at),
          }}
        />
      )}
    </div>
  );
}
