import type { ReactNode } from "react";
import styles from "./StatusChip.module.css";

/** A word of status: Due is the only filled chip; the others are outlined. The icon is decoration. */
export function StatusChip({
  kind = "outline",
  icon,
  children,
}: {
  kind?: "due" | "outline" | "experimental";
  icon?: ReactNode;
  children: ReactNode;
}) {
  return (
    <span className={[styles.chip, styles[kind]].join(" ")}>
      {icon && (
        <span className={styles.icon} aria-hidden="true">
          {icon}
        </span>
      )}
      {children}
    </span>
  );
}
