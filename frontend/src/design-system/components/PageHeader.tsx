import { ArrowLeft } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { useTranslation } from "react-i18next";
import styles from "./PageHeader.module.css";

/**
 * The top of an inner page: the way back (an arrow named after the parent, whose title shows from
 * 900 px), the title with what sits beside it, one line of meta, and the page's few actions.
 */
export function PageHeader({
  back,
  title,
  aside,
  meta,
  actions,
  titleClassName,
}: {
  /** Where the arrow goes and what it is called: the parent's title. */
  back?: { to: string; label: string };
  title: ReactNode;
  /** Sits right of the title: a status badge, a role. */
  aside?: ReactNode;
  /** One line under the title. */
  meta?: ReactNode;
  /** Icon buttons and the "more" menu. */
  actions?: ReactNode;
  titleClassName?: string;
}) {
  const { t } = useTranslation();
  return (
    <header className={styles.header}>
      {back && (
        <Link to={back.to} className={styles.back} aria-label={t("common.backTo", { title: back.label })}>
          <ArrowLeft aria-hidden="true" />
          <span className={styles.backText}>{back.label}</span>
        </Link>
      )}
      <div className={styles.row}>
        <div className={styles.titles}>
          <h1 className={titleClassName}>{title}</h1>
          {aside}
        </div>
        {actions && <div className={styles.actions}>{actions}</div>}
      </div>
      {meta && <p className={["text-secondary", styles.meta].join(" ")}>{meta}</p>}
    </header>
  );
}
