import type { HTMLAttributes } from "react";
import styles from "./Card.module.css";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div {...props} className={[styles.card, className].filter(Boolean).join(" ")} />;
}
