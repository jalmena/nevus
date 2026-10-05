import type { ReactNode } from "react";
import { Card } from "@/design-system/components/Card";
import { Disclosure } from "@/design-system/components/Disclosure";
import styles from "./settings.module.css";

/** A settings group: a card with its heading or, folded, a disclosure that opens on demand or from its link. */
export function Group({
  folded = false,
  id,
  title,
  hint,
  children,
}: {
  folded?: boolean;
  id: string;
  title: string;
  hint?: string;
  children: ReactNode;
}) {
  if (folded) {
    return (
      <Disclosure id={id} title={title} hint={hint}>
        {children}
      </Disclosure>
    );
  }
  return (
    <Card className={styles.group} id={id}>
      <h2 className={styles.subheading}>{title}</h2>
      {children}
    </Card>
  );
}
