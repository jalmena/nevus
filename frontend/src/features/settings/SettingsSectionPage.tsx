import { Navigate, useParams } from "react-router";
import { AdminSettings, InstanceSection } from "@/features/admin/AdminSettings";
import { BackupSettings } from "@/features/admin/BackupSettings";
import { UsersAdmin } from "@/features/admin/UsersAdmin";
import { WebhookSettings } from "@/features/admin/WebhookSettings";
import { useSession } from "@/lib/auth/session";
import { AboutSection } from "./AboutSection";
import { AccountSection } from "./AccountSection";
import { AppearanceSection } from "./AppearanceSection";
import { PushSettings } from "./PushSettings";
import { ReferenceCardSettings } from "./ReferenceCardSettings";
import { ReminderSettings } from "./ReminderSettings";
import { SecondFactorSettings } from "./SecondFactorSettings";
import { YourDataSection } from "./YourDataSection";

/** One settings section as its own page under /settings/{section}. */
export function SettingsSectionPage() {
  const { section = "" } = useParams();
  const user = useSession().data?.user;
  if (!user) return null;
  const admin = user.role === "admin";
  switch (section) {
    case "account":
      return <AccountSection admin={admin} />;
    case "appearance":
      return <AppearanceSection admin={admin} />;
    case "reminders":
      return <ReminderSettings admin={admin} />;
    case "notifications":
      return <PushSettings admin={admin} />;
    case "second-factor":
      return <SecondFactorSettings admin={admin} />;
    case "reference-card":
      return <ReferenceCardSettings admin={admin} />;
    case "your-data":
      return <YourDataSection admin={admin} />;
    case "about":
      return <AboutSection admin={admin} />;
    case "accounts":
      return admin ? <UsersAdmin /> : <Navigate to="/settings" replace />;
    case "email":
      return admin ? <AdminSettings /> : <Navigate to="/settings" replace />;
    case "webhooks":
      return admin ? <WebhookSettings /> : <Navigate to="/settings" replace />;
    case "backups":
      return admin ? <BackupSettings /> : <Navigate to="/settings" replace />;
    case "instance":
      return admin ? <InstanceSection /> : <Navigate to="/settings" replace />;
    default:
      return <Navigate to="/settings" replace />;
  }
}
