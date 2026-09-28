import { useTranslation } from "react-i18next";
import { VIEWS, type View } from "./zones";
import styles from "./ViewToggle.module.css";

export function ViewToggle({ view, onChange }: { view: View; onChange: (view: View) => void }) {
  const { t } = useTranslation();
  return (
    <div className={styles.toggle} role="radiogroup" aria-label={t("bodymap.view")}>
      {VIEWS.map((option) => (
        <button
          key={option}
          type="button"
          role="radio"
          aria-checked={option === view}
          className={option === view ? styles.active : undefined}
          onClick={() => onChange(option)}
        >
          {t(`bodymap.views.${option}`)}
        </button>
      ))}
    </div>
  );
}
