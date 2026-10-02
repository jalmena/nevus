import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { Button } from "@/design-system/components/Button";
import { useSession } from "@/lib/auth/session";
import type { ImageOut } from "@/lib/images";
import { formatMm, useDeleteMeasurement, useVisitMeasurements } from "@/lib/measurements";
import styles from "./measure.module.css";

/** The visit's measurements, and a way into the measuring tool for each photo. */
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
  const session = useSession();
  const measurements = useVisitMeasurements(observationId);
  const remove = useDeleteMeasurement();
  const locale = i18n.resolvedLanguage ?? "en";
  const showUncertainty = session.data?.user.show_uncertainty ?? true;
  const two = new Intl.NumberFormat(locale, { maximumFractionDigits: 2, minimumFractionDigits: 2 });
  const whole = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
  return (
    <section className={styles.panel} aria-labelledby="measurements-heading">
      <h2 id="measurements-heading">{t("measure.visitTitle")}</h2>
      {measurements.data && measurements.data.length === 0 && (
        <p className="text-secondary">{images.length > 0 ? t("measure.noneYet") : t("measure.needPhoto")}</p>
      )}
      <ul className={styles.measurements}>
        {measurements.data?.map((m) => (
          <li key={m.id}>
            <span className="numeric">
              {formatMm(m.longest_mm, m.sigma_longest_mm, locale, showUncertainty)} ×{" "}
              {formatMm(m.perpendicular_mm, m.sigma_perpendicular_mm, locale, showUncertainty)} ·{" "}
              {t(`measure.scaleKinds.${m.scale_kind}`)}
              {m.flags.includes("tilted") && <> · {t("measure.tiltedShort")}</>}
              {m.descriptors && (
                <>
                  {" "}
                  · {t("measure.compactnessShort", { value: two.format(m.descriptors.shape.compactness) })}
                </>
              )}
              {m.descriptors?.colour && (
                <> · {t("measure.contrastShort", { value: whole.format(m.descriptors.colour.contrast) })}</>
              )}
            </span>
            {canEdit && (
              <Button variant="quiet" onClick={() => remove.mutate(m.id)} disabled={remove.isPending}>
                {t("measure.delete")}
              </Button>
            )}
          </li>
        ))}
      </ul>
      {canEdit && images.length > 0 && (
        <div className={styles.actions}>
          {images.map((image, index) => (
            <Link
              key={image.id}
              className={styles.measureLink}
              to={`/observations/${observationId}/measure/${image.id}`}
            >
              {images.length > 1 ? t("measure.measurePhotoN", { n: index + 1 }) : t("measure.measurePhoto")}
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
