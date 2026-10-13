import { useEffect, useRef, type ReactNode } from "react";
import { usePageChrome, setTitleInView, type Chrome } from "@/app/chrome";
import styles from "./PageHeader.module.css";

/**
 * The top of a page, in the content: the title, one meta line, a strip of facts. It also tells the
 * shell what to show around the page (the way back, the icon actions, the menu, the primary action).
 */
export function PageHeader({
  title,
  meta,
  chip,
  facts,
  children,
  ...chrome
}: Chrome & {
  title: string;
  /** Items separated by " · ". */
  meta?: ReactNode[];
  /** A status chip at the end of the meta line. */
  chip?: ReactNode;
  /** Numbers that matter, as label and value pairs; pairs without a value are left out. */
  facts?: { label: string; value: ReactNode | null | undefined }[];
  children?: ReactNode;
}) {
  const heading = useRef<HTMLHeadingElement>(null);
  usePageChrome({ ...chrome, title });
  useEffect(() => {
    const element = heading.current;
    if (!element || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(([entry]) => setTitleInView(entry?.isIntersecting ?? true), {
      rootMargin: "-56px 0px 0px 0px",
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  const items = (meta ?? []).filter((item) => item !== null && item !== undefined && item !== "");
  const shown = (facts ?? []).filter(
    (fact) => fact.value !== null && fact.value !== undefined && fact.value !== "",
  );
  return (
    <header className={styles.header}>
      <h1 ref={heading} className={styles.title}>
        {title}
      </h1>
      {(items.length > 0 || chip) && (
        <p className={styles.meta}>
          {items.every((item) => typeof item === "string")
            ? items.join(" · ")
            : items.map((item, index) => (
                <span key={index} className={styles.metaItem}>
                  {index > 0 && <span aria-hidden="true">{" · "}</span>}
                  {item}
                </span>
              ))}
          {chip && <span className={styles.chip}>{chip}</span>}
        </p>
      )}
      {shown.length > 0 && (
        <dl className={styles.facts}>
          {shown.map((fact) => (
            <div key={fact.label}>
              <dt>{fact.label}</dt>
              <dd className="numeric">{fact.value}</dd>
            </div>
          ))}
        </dl>
      )}
      {children}
    </header>
  );
}
