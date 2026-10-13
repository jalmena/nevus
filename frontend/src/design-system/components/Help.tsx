import { CircleHelp } from "lucide-react";
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "./Button";
import { IconButton } from "./IconButton";
import { Sheet } from "./Sheet";
import styles from "./Help.module.css";

/** The long explanation, on demand: a help icon or a "Learn more" button that opens a sheet. */
export function Help({
  title,
  label,
  as = "icon",
  children,
}: {
  title: string;
  /** The accessible name of the icon; the title by default. */
  label?: string;
  as?: "icon" | "text";
  children: ReactNode;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  return (
    <>
      {as === "icon" ? (
        <IconButton label={label ?? title} icon={<CircleHelp />} onClick={() => setOpen(true)} />
      ) : (
        <Button variant="quiet" className={styles.inline} onClick={() => setOpen(true)}>
          {t("common.learnMore")}
        </Button>
      )}
      <Sheet open={open} title={title} onClose={() => setOpen(false)}>
        {children}
      </Sheet>
    </>
  );
}
