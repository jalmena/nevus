import { useId, type ReactNode } from "react";
import styles from "./Switch.module.css";

/** A setting that is on or off: a labelled switch, saved as soon as it moves. */
export function Switch({
  label,
  hint,
  checked,
  onChange,
  disabled = false,
}: {
  label: ReactNode;
  hint?: ReactNode;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  return (
    <div className={styles.row}>
      <span className={styles.text}>
        <span id={id}>{label}</span>
        {hint && (
          <span id={hintId} className={styles.hint}>
            {hint}
          </span>
        )}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-labelledby={id}
        aria-describedby={hintId}
        className={styles.track}
        disabled={disabled}
        onClick={() => onChange(!checked)}
      >
        <span className={styles.thumb} />
      </button>
    </div>
  );
}
