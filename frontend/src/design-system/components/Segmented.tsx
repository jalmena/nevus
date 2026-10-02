import { useRef, type KeyboardEvent } from "react";
import styles from "./Segmented.module.css";

/** A small set of mutually exclusive choices shown side by side. Arrow keys move the choice, as in any radio group. */
export function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
  wide = false,
}: {
  label: string;
  options: readonly { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
  /** Fill the row, sharing the width equally (for longer labels on phones). */
  wide?: boolean;
}) {
  const group = useRef<HTMLDivElement>(null);

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key];
    if (step === undefined) return;
    event.preventDefault();
    const index = options.findIndex((option) => option.value === value);
    const next = options[(index + step + options.length) % options.length];
    if (!next) return;
    onChange(next.value);
    group.current?.querySelector<HTMLButtonElement>(`[data-value="${next.value}"]`)?.focus();
  }

  return (
    <div
      ref={group}
      className={[styles.group, wide ? styles.wide : ""].join(" ")}
      role="radiogroup"
      aria-label={label}
    >
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          data-value={option.value}
          aria-checked={option.value === value}
          tabIndex={option.value === value ? 0 : -1}
          className={option.value === value ? styles.active : undefined}
          onClick={() => onChange(option.value)}
          onKeyDown={onKeyDown}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
