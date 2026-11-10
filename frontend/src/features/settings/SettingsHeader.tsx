import type { TFunction } from "i18next";
import {
  Archive,
  Bell,
  Database,
  IdCard,
  Info,
  Mail,
  Palette,
  Server,
  Shield,
  Smartphone,
  User,
  Users,
  Webhook,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useMediaQuery, type Chrome } from "@/app/chrome";
import { PageHeader } from "@/design-system/components/PageHeader";
import { usePushOffered } from "@/lib/push";

export interface SettingsSection {
  id: string;
  label: (t: TFunction) => string;
  icon: LucideIcon;
  admin?: boolean;
  group: "account" | "reminders" | "security" | "measuring" | "yourData" | "administration" | "about";
}

/** Every settings section, in the order the rows and the rail show them. */
export const SECTIONS: SettingsSection[] = [
  { id: "account", label: (t) => t("settings.account"), icon: User, group: "account" },
  { id: "appearance", label: (t) => t("settings.appearance"), icon: Palette, group: "account" },
  { id: "reminders", label: (t) => t("reminders.settingsTitle"), icon: Bell, group: "reminders" },
  { id: "notifications", label: (t) => t("push.title"), icon: Smartphone, group: "reminders" },
  { id: "second-factor", label: (t) => t("secondFactor.title"), icon: Shield, group: "security" },
  { id: "reference-card", label: (t) => t("card.title"), icon: IdCard, group: "measuring" },
  { id: "your-data", label: (t) => t("data.title"), icon: Database, group: "yourData" },
  { id: "accounts", label: (t) => t("accounts.title"), icon: Users, admin: true, group: "administration" },
  { id: "email", label: (t) => t("admin.emailTitle"), icon: Mail, admin: true, group: "administration" },
  { id: "webhooks", label: (t) => t("webhooks.title"), icon: Webhook, admin: true, group: "administration" },
  { id: "backups", label: (t) => t("backups.title"), icon: Archive, admin: true, group: "administration" },
  {
    id: "instance",
    label: (t) => t("admin.instanceTitle"),
    icon: Server,
    admin: true,
    group: "administration",
  },
  { id: "about", label: (t) => t("settings.about"), icon: Info, group: "about" },
];

/** The rail's context block inside Settings: the sections the user may open, less any `hidden`. */
export function settingsRail(t: TFunction, admin: boolean, hidden: readonly string[] = []): Chrome["rail"] {
  return {
    heading: t("settings.title"),
    items: SECTIONS.filter((section) => (admin || !section.admin) && !hidden.includes(section.id)).map(
      (section) => {
        const Icon = section.icon;
        return { to: `/settings/${section.id}`, label: section.label(t), icon: <Icon /> };
      },
    ),
  };
}

/** The sections this user is not offered here: the same in the rail and in the list on a phone. */
export function useHiddenSections(admin: boolean): string[] {
  return usePushOffered(admin) ? [] : ["notifications"];
}

/** The header of a settings sub-page: back to the list on a phone, the sections in the rail on a desktop. */
export function SettingsHeader({
  admin,
  title,
  meta,
  chip,
  children,
  ...chrome
}: Omit<Chrome, "back" | "rail" | "title"> & {
  admin: boolean;
  title: string;
  meta?: ReactNode[];
  chip?: ReactNode;
  children?: ReactNode;
}) {
  const { t } = useTranslation();
  const desktop = useMediaQuery("(min-width: 900px)");
  const hidden = useHiddenSections(admin);
  return (
    <PageHeader
      {...chrome}
      back={desktop ? undefined : { to: "/settings", label: t("settings.title") }}
      title={title}
      meta={meta}
      chip={chip}
      rail={settingsRail(t, admin, hidden)}
    >
      {children}
    </PageHeader>
  );
}
