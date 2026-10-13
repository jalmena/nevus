import { ChevronRight } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import styles from "./Row.module.css";

/** A list of rows separated by hairlines; no card around it. */
export function RowList({
  children,
  label,
  className,
}: {
  children: ReactNode;
  label?: string;
  className?: string;
}) {
  return (
    <ul className={[styles.list, className].filter(Boolean).join(" ")} aria-label={label}>
      {children}
    </ul>
  );
}

/**
 * One row: a leading image, initial or icon; a title and one meta line; one trailing thing. The
 * trailing controls sit beside the row's link or button, never inside it.
 */
export function Row({
  to,
  onClick,
  leading,
  title,
  meta,
  extra,
  trailing,
  selected = false,
  chevron,
  ariaLabel,
}: {
  to?: string;
  onClick?: () => void;
  leading?: ReactNode;
  title: ReactNode;
  meta?: ReactNode;
  /** Between the title and the meta: a strip of thumbnails, a progress bar. */
  extra?: ReactNode;
  trailing?: ReactNode;
  selected?: boolean;
  /** Shown when the row navigates and nothing else trails it. */
  chevron?: boolean;
  ariaLabel?: string;
}) {
  const body = (
    <>
      {leading && <span className={styles.leading}>{leading}</span>}
      <span className={styles.text}>
        <span className={styles.title}>{title}</span>
        {extra}
        {meta && <span className={styles.meta}>{meta}</span>}
      </span>
    </>
  );
  const interactive = Boolean(to || onClick);
  return (
    <li
      className={[styles.row, interactive ? styles.interactive : "", selected ? styles.selected : ""].join(
        " ",
      )}
    >
      {to ? (
        <Link to={to} className={styles.main} aria-label={ariaLabel}>
          {body}
        </Link>
      ) : onClick ? (
        <button
          type="button"
          className={styles.main}
          onClick={onClick}
          aria-label={ariaLabel}
          aria-pressed={selected || undefined}
        >
          {body}
        </button>
      ) : (
        <div className={styles.main}>{body}</div>
      )}
      {trailing && <span className={styles.trailing}>{trailing}</span>}
      {!trailing && (chevron ?? Boolean(to)) && (
        <ChevronRight className={styles.chevron} aria-hidden="true" />
      )}
    </li>
  );
}

/** A 40 px circle with a name's initial, for persons. */
export function Initial({ name }: { name: string }) {
  return (
    <span className={styles.initial} aria-hidden="true">
      {name.trim().charAt(0).toUpperCase()}
    </span>
  );
}

/** A 48 px thumbnail on the photo frame, or an empty frame. */
export function Thumb({ src, alt = "", size = 48 }: { src?: string | null; alt?: string; size?: number }) {
  return src ? (
    <img src={src} alt={alt} width={size} height={size} className={styles.thumb} loading="lazy" />
  ) : (
    <span className={styles.thumb} style={{ width: size, height: size }} aria-hidden="true" />
  );
}
