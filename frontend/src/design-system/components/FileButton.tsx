import type { ChangeEvent } from "react";
import buttonStyles from "./Button.module.css";
import styles from "./FileButton.module.css";

/**
 * A file input that looks like a button. A label wraps the input rather than a button wrapping it,
 * so there is one interactive control, it keeps its accessible name, and the keyboard reaches it.
 */
export function FileButton({
  label,
  onFiles,
  accept = "image/*",
  capture,
  multiple = false,
  disabled = false,
  variant = "primary",
}: {
  label: string;
  onFiles: (files: File[]) => void;
  accept?: string;
  capture?: "environment" | "user";
  multiple?: boolean;
  disabled?: boolean;
  variant?: "primary" | "secondary";
}) {
  function onChange(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (files.length > 0) onFiles(files);
  }
  return (
    <label
      className={[
        buttonStyles.button,
        buttonStyles[variant],
        styles.file,
        disabled ? styles.disabled : "",
      ].join(" ")}
    >
      <input
        type="file"
        className={styles.input}
        accept={accept}
        capture={capture}
        multiple={multiple}
        disabled={disabled}
        onChange={onChange}
      />
      <span>{label}</span>
    </label>
  );
}
