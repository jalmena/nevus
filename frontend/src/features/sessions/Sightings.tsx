import { useTranslation } from "react-i18next";
import { Row, RowList, Thumb } from "@/design-system/components/Row";
import { Section } from "@/design-system/components/Section";
import { shortDate } from "@/lib/dates";
import { useSightings } from "@/lib/sessions";

/** On a mark's page: where it was seen in full-body sessions. */
export function Sightings({ lesionId }: { lesionId: string }) {
  const { t, i18n } = useTranslation();
  const sightings = useSightings(lesionId);
  if (!sightings.data || sightings.data.length === 0) return null;
  return (
    <Section title={t("sessions.sightings")}>
      <RowList>
        {sightings.data.map((item) => (
          <Row
            key={item.mark_id}
            to={`/sessions/${item.session_id}/zones/${item.zone}`}
            leading={<Thumb src={item.crop_url} />}
            title={shortDate(i18n.resolvedLanguage, item.started_at)}
            meta={t(`sessions.zones.${item.zone}.name`)}
          />
        ))}
      </RowList>
    </Section>
  );
}
