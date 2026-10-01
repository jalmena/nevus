import { useTranslation } from "react-i18next";
import { Notice } from "@/design-system/components/Notice";
import styles from "./PhotoGallery.module.css";

export const QUALITY_FLAGS = ["blurry", "too_dark", "too_bright", "glare", "low_resolution"] as const;

/** "Saved with quality warnings": what was found and how to take a better photo next time. Never blocking. */
export function QualityNotice({ flags, checking }: { flags: string[]; checking: boolean }) {
  const { t } = useTranslation();
  if (flags.length === 0) {
    return checking ? (
      <p className="text-secondary" role="status">
        {t("quality.checking")}
      </p>
    ) : null;
  }
  return (
    <Notice kind="attention">
      <strong>{t("quality.title")}</strong>
      <ul className={styles.qualityList}>
        {flags.map((flag) => (
          <li key={flag}>{t(`quality.flags.${flag}`, { defaultValue: flag })}</li>
        ))}
      </ul>
      {t("quality.hint")}
    </Notice>
  );
}
