import { useEffect, useState, type ReactNode } from "react";
import styles from "./Disclosure.module.css";

interface Props {
  id: string;
  title: string;
  /** One line under the title, so the tool can be judged without opening it. */
  hint?: string;
  /** Open from the start when something inside is live (an appointment ahead, a session in progress). */
  defaultOpen?: boolean;
  children: ReactNode;
}

/** A tool folded under its title: a native disclosure drawn as a card. The heading stays a heading. */
export function Disclosure({ id, title, hint, defaultOpen = false, children }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  useEffect(() => {
    if (defaultOpen) setOpen(true); // something became live: show it; never fold on the person's behalf
  }, [defaultOpen]);
  return (
    <details
      id={id}
      className={styles.details}
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
      aria-labelledby={`${id}-heading`}
    >
      <summary className={styles.summary}>
        <span className={styles.text}>
          <h2 id={`${id}-heading`} className={styles.title}>
            {title}
          </h2>
          {hint && <span className={styles.hint}>{hint}</span>}
        </span>
        <span className={styles.chevron} aria-hidden="true" />
      </summary>
      <div className={styles.body}>{children}</div>
    </details>
  );
}
