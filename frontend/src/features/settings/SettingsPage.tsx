import { LogOut } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Navigate } from "react-router";
import { useMediaQuery } from "@/app/chrome";
import { Notice } from "@/design-system/components/Notice";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Row, RowList } from "@/design-system/components/Row";
import { GroupLabel } from "@/design-system/components/Section";
import { Select } from "@/design-system/components/Select";
import { Switch } from "@/design-system/components/Switch";
import { useBackupStatus, useEmailSettings, useInstanceSettings, useUsers } from "@/lib/admin";
import { useInstance, useLogout, useSession, useUpdateMe } from "@/lib/auth/session";
import { useTotpStatus } from "@/lib/auth/totp";
import { useExports } from "@/lib/data";
import { supportedLanguages, type Language } from "@/lib/i18n";
import { useWebhooks } from "@/lib/notifications";
import { pushSupported, usePushStatus } from "@/lib/push";
import { SECTIONS, settingsRail, type SettingsSection } from "./SettingsHeader";
import { THEMES } from "./AppearanceSection";
import { useThisDevice } from "./PushSettings";
import styles from "./settings.module.css";

/** The settings on a phone: rows in groups, each opening its section. On a desktop the rail does this. */
export function SettingsPage() {
  const desktop = useMediaQuery("(min-width: 900px)");
  const session = useSession();
  const user = session.data?.user;
  if (!user) return null;
  if (desktop) return <Navigate to="/settings/appearance" replace />;
  return <SettingsRows admin={user.role === "admin"} />;
}

function SettingsRows({ admin }: { admin: boolean }) {
  const { t, i18n } = useTranslation();
  const session = useSession();
  const instance = useInstance();
  const update = useUpdateMe();
  const logout = useLogout();
  const local = instance.data?.auth_mode !== "proxy";
  const totp = useTotpStatus(local);
  const supported = pushSupported();
  const push = usePushStatus(supported);
  const thisDevice = useThisDevice(push.data?.subscriptions);
  const exports = useExports();
  const user = session.data?.user;
  if (!user) return null;
  const dateFormat = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium" });

  const status: Record<string, string | undefined> = {
    account: t(`settings.roles.${user.role}`),
    reminders: user.email_reminders ? t("settings.status.emailOn") : t("settings.status.emailOff"),
    notifications: thisDevice ? t("settings.status.deviceOn") : t("settings.status.deviceOff"),
    "second-factor": totp.data?.enabled
      ? t("settings.status.secondFactorOn", { count: totp.data.recovery_codes_left })
      : t("settings.status.secondFactorOff"),
    "reference-card": user.card_line_mm
      ? t("settings.status.cardVerified", { mm: user.card_line_mm })
      : t("settings.status.cardUnverified"),
    "your-data": t("settings.status.exports", { count: exports.data?.length ?? 0 }),
    about: t("settings.version", { version: instance.data?.version ?? "" }),
  };
  const groups = [
    "account",
    "reminders",
    "security",
    "measuring",
    "yourData",
    "administration",
    "about",
  ] as const;
  const show = (id: string) => {
    if (id === "notifications") return supported && Boolean(push.data?.enabled);
    if (id === "second-factor") return local && Boolean(totp.data);
    return true;
  };

  return (
    <div className={styles.page}>
      <PageHeader title={t("settings.title")} rail={settingsRail(t, admin)} />
      {groups.map((group) => {
        const sections = SECTIONS.filter(
          (section) => section.group === group && (admin || !section.admin) && show(section.id),
        );
        if (sections.length === 0) return null;
        return (
          <div key={group}>
            {group !== "about" && <GroupLabel>{t(`settings.groups.${group}`)}</GroupLabel>}
            <RowList>
              {group === "administration" ? (
                <AdminRows sections={sections} dateFormat={dateFormat} />
              ) : (
                sections.map((section) => {
                  const Icon = section.icon;
                  return (
                    <Row
                      key={section.id}
                      to={`/settings/${section.id}`}
                      leading={<Icon />}
                      title={section.id === "account" ? user.username : section.label(t)}
                      meta={status[section.id]}
                      chevron
                    />
                  );
                })
              )}
              {group === "account" && (
                <>
                  <Row
                    title={t("shell.language")}
                    trailing={
                      <Select
                        label={t("shell.language")}
                        labelHidden
                        value={user.language}
                        onChange={(e) => update.mutate({ language: e.target.value as Language })}
                        options={supportedLanguages.map((code) => ({
                          value: code,
                          label: t(`languages.${code}`),
                        }))}
                      />
                    }
                  />
                  <Row
                    title={t("settings.theme")}
                    trailing={
                      <Select
                        label={t("settings.theme")}
                        labelHidden
                        value={user.theme}
                        onChange={(e) => update.mutate({ theme: e.target.value as (typeof THEMES)[number] })}
                        options={THEMES.map((theme) => ({
                          value: theme,
                          label: t(`settings.themes.${theme}`),
                        }))}
                      />
                    }
                  />
                  <li className={styles.switchRow}>
                    <Switch
                      label={t("settings.showUncertainty")}
                      checked={user.show_uncertainty}
                      onChange={(checked) => update.mutate({ show_uncertainty: checked })}
                    />
                  </li>
                  <Row
                    onClick={() => logout.mutate()}
                    leading={<LogOut />}
                    title={t("settings.signOut")}
                    chevron={false}
                  />
                </>
              )}
            </RowList>
            {group === "account" && update.error && <Notice kind="error">{update.error.message}</Notice>}
          </div>
        );
      })}
    </div>
  );
}

/** The administration rows, each with a status only an administrator may fetch. */
function AdminRows({
  sections,
  dateFormat,
}: {
  sections: SettingsSection[];
  dateFormat: Intl.DateTimeFormat;
}) {
  const { t } = useTranslation();
  const users = useUsers();
  const email = useEmailSettings(true);
  const hooks = useWebhooks();
  const backups = useBackupStatus(true);
  const instance = useInstanceSettings(true);
  const status: Record<string, string | undefined> = {
    accounts: users.data ? t("settings.status.accounts", { count: users.data.length }) : undefined,
    email: email.data
      ? email.data.ready
        ? t("settings.status.emailReady")
        : t("settings.status.emailNotReady")
      : undefined,
    webhooks: hooks.data ? t("settings.status.webhooks", { count: hooks.data.length }) : undefined,
    backups: backups.data
      ? !backups.data.enabled
        ? t("settings.status.backupsOff")
        : backups.data.latest
          ? t("settings.status.backupsLast", {
              date: dateFormat.format(new Date(backups.data.latest.created_at)),
            })
          : t("settings.status.backupsNone")
      : undefined,
    instance: instance.data
      ? t("settings.status.language", { language: t(`languages.${instance.data.default_language}`) })
      : undefined,
  };
  return (
    <>
      {sections.map((section) => {
        const Icon = section.icon;
        return (
          <Row
            key={section.id}
            to={`/settings/${section.id}`}
            leading={<Icon />}
            title={section.label(t)}
            meta={status[section.id]}
            chevron
          />
        );
      })}
    </>
  );
}
