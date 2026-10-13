import type { ButtonHTMLAttributes, ReactNode } from "react";
import styles from "./Chip.module.css";

/** A small labelled button with a leading icon: a tool in a row of tools, or an option that toggles. */
export function Chip({
  icon,
  pressed,
  className,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { icon?: ReactNode; pressed?: boolean }) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      {...props}
      className={[styles.chip, pressed ? styles.pressed : "", className].filter(Boolean).join(" ")}
    >
      {icon && (
        <span className={styles.icon} aria-hidden="true">
          {icon}
        </span>
      )}
      {children}
    </button>
  );
}
