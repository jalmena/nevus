import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Card } from "@/design-system/components/Card";
import { Notice } from "@/design-system/components/Notice";
import { useBackupNow, useBackupStatus, useVerifyBackupNow } from "@/lib/admin";
import { formatBytes } from "@/lib/data";
import styles from "@/features/settings/settings.module.css";

/** For administrators: whether the nightly backup runs, the latest one, and whether it would restore. */
export function BackupSettings() {
  const { t, i18n } = useTranslation();
  const status = useBackupStatus(true);
  const backUp = useBackupNow();
  const verify = useVerifyBackupNow();
  const locale = i18n.resolvedLanguage ?? "en";
  const dateFormat = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" });
  if (!status.data) return null;
  const backups = status.data;
  const verification = backups.verification;
  const failure = status.error ?? backUp.error ?? verify.error;

  return (
    <Card className={styles.group}>
      <h2 className={styles.subheading}>{t("backups.title")}</h2>
      {!backups.enabled ? (
        <p className="text-secondary">{t("backups.off")}</p>
      ) : (
        <>
          <p className="text-secondary">
            {t("backups.intro", { hour: String(backups.backup_hour).padStart(2, "0") })}{" "}
            {backups.verify_days > 0
              ? t("backups.verifyEvery", { count: backups.verify_days })
              : t("backups.verifyNever")}
          </p>
          <p>
            {backups.latest
              ? t("backups.latest", {
                  count: backups.count,
                  date: dateFormat.format(new Date(backups.latest.created_at)),
                  size: formatBytes(backups.latest.bytes, locale),
                })
              : t("backups.none")}
          </p>
          {verification ? (
            verification.ok ? (
              <Notice kind="success">
                {t("backups.verifiedOk", {
                  date: dateFormat.format(new Date(verification.checked_at)),
                  archive: verification.archive,
                  count: verification.blobs_in_archive ?? 0,
                })}
              </Notice>
            ) : (
              <Notice kind="error">
                {t("backups.verifiedBad", {
                  date: dateFormat.format(new Date(verification.checked_at)),
                  archive: verification.archive ?? "",
                })}
                <ul>
                  {verification.problems.map((problem) => (
                    <li key={problem}>
                      {t(`backups.problems.${problem.split(":")[0] ?? problem}`, { defaultValue: problem })}
                    </li>
                  ))}
                </ul>
              </Notice>
            )
          ) : (
            <p className="text-secondary">{t("backups.neverVerified")}</p>
          )}
          <div className={styles.userActions}>
            <Button
              variant="secondary"
              disabled={backUp.isPending || backups.backup_queued}
              onClick={() => backUp.mutate()}
            >
              {backups.backup_queued ? t("backups.backingUp") : t("backups.backUpNow")}
            </Button>
            <Button
              variant="secondary"
              disabled={verify.isPending || backups.verification_queued || !backups.latest}
              onClick={() => verify.mutate()}
            >
              {backups.verification_queued ? t("backups.verifying") : t("backups.verifyNow")}
            </Button>
          </div>
        </>
      )}
      {failure && <Notice kind="error">{failure.message}</Notice>}
    </Card>
  );
}
