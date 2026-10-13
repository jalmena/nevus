import { Check, Copy, Unlink } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Help } from "@/design-system/components/Help";
import { IconButton } from "@/design-system/components/IconButton";
import { Notice } from "@/design-system/components/Notice";
import { PageHeader } from "@/design-system/components/PageHeader";
import { useConfirm } from "@/lib/confirm/ConfirmProvider";
import { useCalendarFeed, useNewCalendarFeed, useStopCalendarFeed } from "@/lib/notifications";
import type { PersonOut } from "@/lib/persons";
import { personRail } from "./personRail";
import styles from "./persons.module.css";

/** A secret link a calendar app subscribes to: next photo dates and appointments, reminded natively. */
export function CalendarLink({ person }: { person: PersonOut }) {
  const { t, i18n } = useTranslation();
  const confirm = useConfirm();
  const feed = useCalendarFeed(person.id);
  const make = useNewCalendarFeed(person.id);
  const stop = useStopCalendarFeed(person.id);
  const [copied, setCopied] = useState(false);
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium" });
  const url = make.data?.url;
  const linked = Boolean(feed.data?.exists || url);

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
    <div className={styles.page}>
      <PageHeader
        back={{ to: `/persons/${person.id}`, label: person.display_name }}
        title={t("calendar.title")}
        meta={[
          feed.data?.exists
            ? t("calendar.linkedSince", {
                date: feed.data.created_at ? dateFormat.format(new Date(feed.data.created_at)) : "",
              })
            : feed.data
              ? t("calendar.notLinked")
              : null,
        ]}
        rail={personRail(t, person.id, person.display_name)}
        primary={{
          label: linked ? t("calendar.again") : t("calendar.make"),
          pending: make.isPending,
          onClick: () => make.mutate(),
        }}
        menu={
          linked
            ? [
                {
                  label: t("calendar.stop"),
                  icon: <Unlink />,
                  danger: true,
                  onSelect: () => {
                    void confirm({
                      title: t("calendar.stopQuestion"),
                      text: t("calendar.stopNote"),
                      action: t("calendar.stop"),
                      danger: true,
                    }).then((yes) => yes && stop.mutate(undefined, { onSuccess: () => make.reset() }));
                  },
                },
              ]
            : []
        }
      >
        <p className={["text-secondary", styles.intro].join(" ")}>
          {t("calendar.hint")}
          <Help title={t("calendar.title")} as="text">
            <p>{t("calendar.intro")}</p>
          </Help>
        </p>
      </PageHeader>
      {url ? (
        <div className={styles.switchRow}>
          <span className="text-secondary">{t("calendar.link")}</span>
          <div className={styles.link}>
            <input readOnly value={url} onFocus={(e) => e.target.select()} aria-label={t("calendar.link")} />
            <IconButton
              label={copied ? t("calendar.copied") : t("calendar.copy")}
              icon={copied ? <Check /> : <Copy />}
              onClick={() => void copy()}
            />
          </div>
          <Notice kind="attention">{t("calendar.warning")}</Notice>
        </div>
      ) : feed.data?.exists ? (
        <p>
          {t("calendar.exists", {
            date: feed.data.created_at ? dateFormat.format(new Date(feed.data.created_at)) : "",
          })}
        </p>
      ) : (
        feed.data && <p className="text-secondary">{t("calendar.empty")}</p>
      )}
      {(make.error ?? stop.error) && <Notice kind="error">{(make.error ?? stop.error)?.message}</Notice>}
    </div>
  );
}
