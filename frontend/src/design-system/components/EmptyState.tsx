import type { ReactNode } from "react";
import styles from "./EmptyState.module.css";

/** One sentence saying what will appear here, a reason, and one action. No illustrations. */
export function EmptyState({ title, text, action }: { title: string; text: string; action?: ReactNode }) {
  return (
    <section className={styles.empty}>
      <h2>{title}</h2>
      <p className="text-secondary">{text}</p>
      {action}
    </section>
  );
}
