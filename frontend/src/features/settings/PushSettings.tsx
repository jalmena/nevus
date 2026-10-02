import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Card } from "@/design-system/components/Card";
import { Notice } from "@/design-system/components/Notice";
import {
  currentSubscription,
  pushSupported,
  useSubscribeDevice,
  useTestPush,
  useUnsubscribeDevice,
  usePushStatus,
} from "@/lib/push";
import styles from "./settings.module.css";

/** Notifications to this device when marks are due, behind the server's flag and the browser's support. */
export function PushSettings() {
  const { t } = useTranslation();
  const supported = pushSupported();
  const status = usePushStatus(supported);
  const subscribe = useSubscribeDevice();
  const unsubscribe = useUnsubscribeDevice();
  const test = useTestPush();
  const [thisDevice, setThisDevice] = useState<boolean | null>(null);
  const count = status.data?.subscriptions;

  useEffect(() => {
    let alive = true;
    void currentSubscription().then((subscription) => {
      if (alive) setThisDevice(Boolean(subscription));
    });
    return () => {
      alive = false;
    };
  }, [count]);

  if (!supported || !status.data?.enabled) return null;
  const failure = subscribe.error ?? unsubscribe.error ?? test.error;
  return (
    <Card className={styles.group}>
      <h2 className={styles.subheading}>{t("push.title")}</h2>
      <p className="text-secondary">{t("push.intro")}</p>
      <p>
        <span>{thisDevice ? t("push.onThisDevice") : t("push.offThisDevice")}</span>{" "}
        <span>{t("push.devices", { count: count ?? 0 })}</span>
      </p>
      <div className={styles.userActions}>
        {thisDevice ? (
          <Button
            variant="secondary"
            disabled={unsubscribe.isPending}
            onClick={() => unsubscribe.mutate(undefined, { onSuccess: () => setThisDevice(false) })}
          >
            {t("push.turnOff")}
          </Button>
        ) : (
          <Button
            disabled={subscribe.isPending || !status.data.public_key}
            onClick={() =>
              subscribe.mutate(status.data?.public_key ?? "", { onSuccess: () => setThisDevice(true) })
            }
          >
            {t("push.turnOn")}
          </Button>
        )}
        <Button variant="secondary" disabled={test.isPending || !count} onClick={() => test.mutate()}>
          {t("push.test")}
        </Button>
      </div>
      {test.data && (
        <Notice kind={test.data.sent > 0 ? "success" : "attention"}>
          {t("push.tested", { sent: test.data.sent, failed: test.data.failed })}
        </Notice>
      )}
      {failure && <Notice kind="error">{failure.message}</Notice>}
      <p className="text-secondary">{t("push.note")}</p>
    </Card>
  );
}
