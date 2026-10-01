import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { useCalendarFeed, useNewCalendarFeed, useStopCalendarFeed } from "@/lib/notifications";
import styles from "./persons.module.css";

/** A secret link a calendar app subscribes to: next photo dates and appointments, reminded natively. */
export function CalendarLink({ personId }: { personId: string }) {
  const { t, i18n } = useTranslation();
  const feed = useCalendarFeed(personId);
  const make = useNewCalendarFeed(personId);
  const stop = useStopCalendarFeed(personId);
  const [copied, setCopied] = useState(false);
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium" });
  const url = make.data?.url;

  async function copy() {
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section className={styles.mapSection} aria-labelledby="calendar-heading">
      <h2 id="calendar-heading">{t("calendar.title")}</h2>
      <p className="text-secondary">{t("calendar.intro")}</p>
      {url ? (
        <div className={styles.calendar}>
          <label className={styles.calendarField}>
            <span>{t("calendar.link")}</span>
            <input readOnly value={url} onFocus={(e) => e.target.select()} />
          </label>
          <Button variant="secondary" onClick={() => void copy()}>
            {copied ? t("calendar.copied") : t("calendar.copy")}
          </Button>
          <Notice kind="attention">{t("calendar.warning")}</Notice>
        </div>
      ) : (
        feed.data?.exists && (
          <p>
            {t("calendar.exists", {
              date: feed.data.created_at ? dateFormat.format(new Date(feed.data.created_at)) : "",
            })}
          </p>
        )
      )}
      <div className={styles.actions}>
        <Button onClick={() => make.mutate()} disabled={make.isPending}>
          {feed.data?.exists || url ? t("calendar.again") : t("calendar.make")}
        </Button>
        {(feed.data?.exists || url) && (
          <Button variant="quiet" onClick={() => stop.mutate(undefined, { onSuccess: () => make.reset() })}>
            {t("calendar.stop")}
          </Button>
        )}
      </div>
      {(make.error || stop.error) && <Notice kind="error">{(make.error ?? stop.error)?.message}</Notice>}
    </section>
  );
}
