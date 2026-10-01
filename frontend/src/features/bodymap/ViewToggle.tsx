import { useTranslation } from "react-i18next";
import { Segmented } from "@/design-system/components/Segmented";
import { VIEWS, type View } from "./zones";

export function ViewToggle({ view, onChange }: { view: View; onChange: (view: View) => void }) {
  const { t } = useTranslation();
  return (
    <Segmented
      label={t("bodymap.view")}
      options={VIEWS.map((option) => ({ value: option, label: t(`bodymap.views.${option}`) }))}
      value={view}
      onChange={onChange}
      wide
    />
  );
}
