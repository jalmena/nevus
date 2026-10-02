import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { useSession } from "@/lib/auth/session";
import { useOutbox } from "@/lib/offline/useOutbox";
import styles from "./capture.module.css";

/** A quiet line under the brand bar: offline, or visits waiting to upload, and what happened to them. */
export function OutboxBar() {
  const { t } = useTranslation();
  const session = useSession();
  const { visits, online, syncNow } = useOutbox(session.data?.user.id);
  const failed = visits.filter((v) => v.status === "failed").length;
  const uploading = visits.some((v) => v.status === "uploading");
  if (online && visits.length === 0) return null;
  return (
    <div className={styles.bar} role="status">
      <span>
        {!online && <strong>{t("offline.offline")} </strong>}
        {visits.length > 0 &&
          (uploading ? t("offline.uploading") : t("offline.waiting", { count: visits.length }))}
        {failed > 0 && !uploading && <> · {t("offline.failed", { count: failed })}</>}
      </span>
      {online && visits.length > 0 && !uploading && (
        <Button variant="quiet" onClick={() => syncNow()}>
          {t("offline.uploadNow")}
        </Button>
      )}
    </div>
  );
}
