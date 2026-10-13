import type { ReactNode } from "react";
import styles from "./EmptyState.module.css";

/** One sentence saying what will appear here and what to do; the action is the page's primary. */
export function EmptyState({ children }: { children: ReactNode }) {
  return <p className={styles.empty}>{children}</p>;
}
