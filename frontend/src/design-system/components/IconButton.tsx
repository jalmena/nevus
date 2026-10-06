import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import buttonStyles from "./Button.module.css";
import styles from "./IconButton.module.css";

type Variant = "primary" | "secondary" | "quiet" | "danger";

/**
 * A button whose meaning is carried by an icon. It always has an accessible name (the label); the
 * label is also shown as text when `showLabel` is true, or from 900 px when it is "desktop".
 */
export const IconButton = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & {
    label: string;
    icon: ReactNode;
    showLabel?: boolean | "desktop";
    variant?: Variant;
  }
>(function IconButton({ label, icon, showLabel = false, variant = "quiet", className, ...props }, ref) {
  const textClass =
    showLabel === true ? styles.text : showLabel === "desktop" ? styles.textDesktop : styles.textHidden;
  return (
    <button
      ref={ref}
      type="button"
      aria-label={showLabel === true ? undefined : label}
      title={showLabel === true ? undefined : label}
      {...props}
      className={[buttonStyles.button, buttonStyles[variant], styles.iconButton, className]
        .filter(Boolean)
        .join(" ")}
    >
      <span className={styles.icon} aria-hidden="true">
        {icon}
      </span>
      <span className={textClass}>{label}</span>
    </button>
  );
});
