import { Ruler, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { IconButton } from "@/design-system/components/IconButton";
import { Row, RowList } from "@/design-system/components/Row";
import { Section } from "@/design-system/components/Section";
import { useSession } from "@/lib/auth/session";
import type { ImageOut } from "@/lib/images";
import { formatMm, useDeleteMeasurement, useVisitMeasurements } from "@/lib/measurements";

/** The visit's measurements as rows; measuring again sits in the section's corner once one exists. */
export function VisitMeasurements({
  observationId,
  images,
  canEdit,
}: {
  observationId: string;
  images: ImageOut[];
  canEdit: boolean;
}) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const session = useSession();
  const measurements = useVisitMeasurements(observationId);
  const remove = useDeleteMeasurement();
  const locale = i18n.resolvedLanguage ?? "en";
  const showUncertainty = session.data?.user.show_uncertainty ?? true;
  const two = new Intl.NumberFormat(locale, { maximumFractionDigits: 2, minimumFractionDigits: 2 });
  const whole = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
  const first = images.find((image) => image.role !== "overview") ?? images[0];
  const measured = (measurements.data?.length ?? 0) > 0;
  return (
    <Section
      title={t("measure.visitTitle")}
      actions={
        canEdit && measured && first ? (
          <IconButton
            label={t("measure.title")}
            icon={<Ruler />}
            showLabel="desktop"
            onClick={() => void navigate(`/observations/${observationId}/measure/${first.id}`)}
          />
        ) : undefined
      }
    >
      {measurements.data && measurements.data.length === 0 && (
        <p className="text-secondary">{images.length > 0 ? t("measure.noneYet") : t("measure.needPhoto")}</p>
      )}
      {measured && (
        <RowList>
          {measurements.data?.map((m) => (
            <Row
              key={m.id}
              title={
                <span className="numeric">
                  {formatMm(m.longest_mm, m.sigma_longest_mm, locale, showUncertainty)} ×{" "}
                  {formatMm(m.perpendicular_mm, m.sigma_perpendicular_mm, locale, showUncertainty)}
                </span>
              }
              meta={[
                t(`measure.scaleKinds.${m.scale_kind}`),
                m.flags.includes("tilted") ? t("measure.tiltedShort") : null,
                m.descriptors
                  ? t("measure.compactnessShort", { value: two.format(m.descriptors.shape.compactness) })
                  : null,
                m.descriptors?.colour
                  ? t("measure.contrastShort", { value: whole.format(m.descriptors.colour.contrast) })
                  : null,
              ]
                .filter(Boolean)
                .join(" · ")}
              trailing={
                canEdit ? (
                  <IconButton
                    label={t("measure.delete")}
                    icon={<Trash2 />}
                    onClick={() => remove.mutate(m.id)}
                    disabled={remove.isPending}
                  />
                ) : undefined
              }
            />
          ))}
        </RowList>
      )}
    </Section>
  );
}
