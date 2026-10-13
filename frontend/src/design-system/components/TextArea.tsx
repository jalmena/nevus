import { useId, type TextareaHTMLAttributes } from "react";
import fieldStyles from "./TextField.module.css";
import styles from "./TextArea.module.css";

/** Free text in the field's shape; the label may be visually hidden when the placeholder says it all. */
export function TextArea({
  label,
  labelHidden = false,
  className,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string; labelHidden?: boolean }) {
  const id = useId();
  return (
    <div className={fieldStyles.field}>
      <label htmlFor={id} className={labelHidden ? styles.hidden : undefined}>
        {label}
      </label>
      <textarea id={id} className={[styles.textarea, className].filter(Boolean).join(" ")} {...props} />
    </div>
  );
}
