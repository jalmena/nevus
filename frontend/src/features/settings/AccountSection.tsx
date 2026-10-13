import { LogOut } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Row, RowList } from "@/design-system/components/Row";
import { useLogout, useSession } from "@/lib/auth/session";
import { SettingsHeader } from "./SettingsHeader";
import styles from "./settings.module.css";

/** Who is signed in, and signing out. */
export function AccountSection({ admin }: { admin: boolean }) {
  const { t } = useTranslation();
  const user = useSession().data?.user;
  const logout = useLogout();
  if (!user) return null;
  return (
    <div className={styles.page}>
      <SettingsHeader admin={admin} title={user.username} meta={[t(`settings.roles.${user.role}`)]} />
      <RowList>
        <Row onClick={() => logout.mutate()} leading={<LogOut />} title={t("settings.signOut")} />
      </RowList>
    </div>
  );
}
