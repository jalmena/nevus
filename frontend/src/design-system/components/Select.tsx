import { useId, type SelectHTMLAttributes } from "react";
import fieldStyles from "./TextField.module.css";
import styles from "./Select.module.css";

/** A choice among a few named things, in the field's shape. The label may be hidden (a row's trailing control). */
export function Select({
  label,
  labelHidden = false,
  options,
  className,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  labelHidden?: boolean;
  options: readonly { value: string; label: string }[];
}) {
  const id = useId();
  const select = (
    <select
      id={id}
      aria-label={labelHidden ? label : undefined}
      className={[styles.select, className].filter(Boolean).join(" ")}
      {...props}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
  if (labelHidden) return select;
  return (
    <div className={fieldStyles.field}>
      <label htmlFor={id}>{label}</label>
      {select}
    </div>
  );
}
