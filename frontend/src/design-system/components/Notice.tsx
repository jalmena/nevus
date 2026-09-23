import type { ReactNode } from "react";
import styles from "./Notice.module.css";

/** Inline message. "attention" is amber and never red: neVus does not alarm about health. */
export function Notice({
  kind = "info",
  children,
}: {
  kind?: "info" | "attention" | "error" | "success";
  children: ReactNode;
}) {
  return (
    <p className={[styles.notice, styles[kind]].join(" ")} role={kind === "error" ? "alert" : "status"}>
      {children}
    </p>
  );
}
