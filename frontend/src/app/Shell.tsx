import { ChevronLeft, CircleHelp, EllipsisVertical, Settings, Users } from "lucide-react";
import { Suspense, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet } from "react-router";
import { Button } from "@/design-system/components/Button";
import { IconButton } from "@/design-system/components/IconButton";
import { Mark } from "@/design-system/components/Mark";
import { Menu } from "@/design-system/components/Menu";
import { Sheet } from "@/design-system/components/Sheet";
import { OutboxBar } from "@/features/capture/OutboxBar";
import { ConfirmProvider } from "@/lib/confirm/ConfirmProvider";
import { SudoProvider } from "@/lib/sudo/SudoProvider";
import { useChrome, useMediaQuery, useTitleInView, type ChromeAction } from "./chrome";
import styles from "./Shell.module.css";

/** The shell: an app bar and a bottom action bar on a phone; a rail and an app bar on a desktop. */
export function Shell() {
  const desktop = useMediaQuery("(min-width: 900px)");
  return (
    <ConfirmProvider>
      <SudoProvider>
        <div className={desktop ? styles.desktop : styles.phone}>
          {desktop && <Rail />}
          <div className={styles.column}>
            <AppBar desktop={desktop} />
            <OutboxBar />
            <main className={styles.main}>
              <Suspense fallback={<p className="text-secondary">…</p>}>
                <Outlet />
              </Suspense>
            </main>
            {!desktop && <ActionBar />}
          </div>
        </div>
      </SudoProvider>
    </ConfirmProvider>
  );
}

function Action({ action, desktop }: { action: ChromeAction; desktop: boolean }) {
  const showLabel = action.showLabel ?? "desktop";
  if (action.to) {
    return (
      <Link
        to={action.to}
        className={styles.actionLink}
        aria-label={showLabel === true || (showLabel === "desktop" && desktop) ? undefined : action.label}
        title={action.label}
      >
        <span className={styles.actionIcon} aria-hidden="true">
          {action.icon}
        </span>
        {(showLabel === true || (showLabel === "desktop" && desktop)) && <span>{action.label}</span>}
      </Link>
    );
  }
  return (
    <IconButton
      label={action.label}
      icon={action.icon}
      showLabel={showLabel}
      onClick={action.onClick}
      disabled={action.disabled}
    />
  );
}

export function AppBar({ desktop }: { desktop: boolean }) {
  const { t } = useTranslation();
  const chrome = useChrome();
  const titleInView = useTitleInView();
  const [helpOpen, setHelpOpen] = useState(false);
  const showTitle = Boolean(chrome.title) && !titleInView;
  return (
    <div className={[styles.appBar, desktop ? styles.appBarDesktop : ""].join(" ")} data-chrome="bar">
      <div className={styles.lead}>
        {chrome.back ? (
          <Link
            to={chrome.back.to}
            className={styles.back}
            aria-label={t("common.backTo", { title: chrome.back.label })}
            title={t("common.backTo", { title: chrome.back.label })}
          >
            <ChevronLeft aria-hidden="true" />
          </Link>
        ) : (
          !desktop && (
            <Link to="/" className={styles.brand} aria-label={t("app.name")}>
              <Mark size={26} />
            </Link>
          )
        )}
        <span
          className={[styles.title, showTitle ? "" : styles.titleHidden].join(" ")}
          aria-hidden={!showTitle}
        >
          {chrome.title}
        </span>
      </div>
      <div className={styles.trail}>
        {chrome.actions?.map((action) => (
          <Action key={action.key} action={action} desktop={desktop} />
        ))}
        {desktop && chrome.instruction && (
          <p className={styles.instruction} role="status">
            {chrome.instruction}
          </p>
        )}
        {desktop && chrome.primary && !chrome.instruction && (
          <Button
            onClick={chrome.primary.onClick}
            disabled={chrome.primary.disabled || chrome.primary.pending}
          >
            {chrome.primary.pending ? t("common.working") : chrome.primary.label}
          </Button>
        )}
        {desktop && chrome.secondary && (
          <Button variant="quiet" onClick={chrome.secondary.onClick}>
            {chrome.secondary.label}
          </Button>
        )}
        {chrome.help && (
          <>
            <IconButton label={t("common.help")} icon={<CircleHelp />} onClick={() => setHelpOpen(true)} />
            <Sheet open={helpOpen} title={chrome.help.title} onClose={() => setHelpOpen(false)}>
              {chrome.help.content}
            </Sheet>
          </>
        )}
        {chrome.menu && chrome.menu.length > 0 && (
          <Menu label={t("shell.more")} icon={<EllipsisVertical />} items={chrome.menu} />
        )}
      </div>
    </div>
  );
}

function ActionBar() {
  const { t } = useTranslation();
  const chrome = useChrome();
  if (!chrome.primary && !chrome.instruction && !chrome.secondary) return null;
  return (
    <div className={styles.actionBar} data-chrome="bar">
      {chrome.secondary && (
        <Button variant="quiet" onClick={chrome.secondary.onClick}>
          {chrome.secondary.label}
        </Button>
      )}
      {chrome.instruction ? (
        <p className={styles.instruction} role="status">
          {chrome.instruction}
        </p>
      ) : (
        chrome.primary && (
          <Button
            className={styles.primary}
            onClick={chrome.primary.onClick}
            disabled={chrome.primary.disabled || chrome.primary.pending}
          >
            {chrome.primary.pending ? t("common.working") : chrome.primary.label}
          </Button>
        )
      )}
    </div>
  );
}

function Rail() {
  const { t } = useTranslation();
  const chrome = useChrome();
  const item = ({ isActive }: { isActive: boolean }) =>
    [styles.railItem, isActive ? styles.railActive : ""].join(" ");
  return (
    <nav className={styles.rail} aria-label={t("shell.navigation")}>
      <Link to="/" className={styles.railBrand} aria-label={t("app.name")}>
        <Mark size={28} />
        <span>{t("app.name")}</span>
      </Link>
      <NavLink to="/" end className={item}>
        <Users aria-hidden="true" />
        <span>{t("shell.persons")}</span>
      </NavLink>
      <NavLink to="/settings" className={item}>
        <Settings aria-hidden="true" />
        <span>{t("settings.title")}</span>
      </NavLink>
      {chrome.rail && (
        <div className={styles.railContext}>
          <p className={styles.railHeading}>{chrome.rail.heading}</p>
          {chrome.rail.items.map((entry) => (
            <NavLink key={entry.to} to={entry.to} end={entry.end} className={item}>
              <span aria-hidden="true" className={styles.railIcon}>
                {entry.icon}
              </span>
              <span>{entry.label}</span>
            </NavLink>
          ))}
        </div>
      )}
    </nav>
  );
}
