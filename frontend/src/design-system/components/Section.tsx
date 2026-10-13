import { useId, type ReactNode } from "react";
import styles from "./Section.module.css";

/** A peer section of a page: its heading, one or two icon actions at its right, its content. */
export function Section({
  title,
  actions,
  chip,
  children,
  className,
}: {
  title: ReactNode;
  actions?: ReactNode;
  /** A status chip after the heading. */
  chip?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  const id = useId();
  return (
    <section className={[styles.section, className].filter(Boolean).join(" ")} aria-labelledby={id}>
      <div className={styles.head}>
        <h2 id={id} className={styles.title}>
          {title}
          {chip && <span className={styles.chip}>{chip}</span>}
        </h2>
        {actions && <div className={styles.actions}>{actions}</div>}
      </div>
      {children}
    </section>
  );
}

/** A group label over a run of rows (settings). */
export function GroupLabel({ children }: { children: ReactNode }) {
  return <p className={styles.group}>{children}</p>;
}
