import { Send } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Help } from "@/design-system/components/Help";
import { Notice } from "@/design-system/components/Notice";
import { StatusChip } from "@/design-system/components/StatusChip";
import {
  currentSubscription,
  pushSupported,
  useSubscribeDevice,
  useTestPush,
  useUnsubscribeDevice,
  usePushStatus,
} from "@/lib/push";
import { SettingsHeader } from "./SettingsHeader";
import styles from "./settings.module.css";

/** Whether this browser holds a subscription; re-checked when the server's count changes. */
export function useThisDevice(count: number | undefined): boolean | null {
  const [thisDevice, setThisDevice] = useState<boolean | null>(null);
  useEffect(() => {
    let alive = true;
    void currentSubscription().then((subscription) => {
      if (alive) setThisDevice(Boolean(subscription));
    });
    return () => {
      alive = false;
    };
  }, [count]);
  return thisDevice;
}

/** Notifications to this device when marks are due, behind the server's flag and the browser's support. */
export function PushSettings({ admin }: { admin: boolean }) {
  const { t } = useTranslation();
  const supported = pushSupported();
  const status = usePushStatus(supported);
  const subscribe = useSubscribeDevice();
  const unsubscribe = useUnsubscribeDevice();
  const test = useTestPush();
  const count = status.data?.subscriptions;
  const thisDevice = useThisDevice(count);
  const [known, setKnown] = useState<boolean | null>(null);
  const on = known ?? thisDevice;

  if (!supported || !status.data?.enabled) return null;
  const failure = subscribe.error ?? unsubscribe.error ?? test.error;
  const publicKey = status.data.public_key ?? "";
  return (
    <div className={styles.page}>
      <SettingsHeader
        admin={admin}
        title={t("push.title")}
        chip={<StatusChip kind="experimental">{t("proposals.experimental")}</StatusChip>}
        meta={[
          on ? t("push.onThisDevice") : t("push.offThisDevice"),
          t("push.devices", { count: count ?? 0 }),
        ]}
        primary={
          on
            ? {
                label: t("push.turnOff"),
                pending: unsubscribe.isPending,
                onClick: () => unsubscribe.mutate(undefined, { onSuccess: () => setKnown(false) }),
              }
            : {
                label: t("push.turnOn"),
                pending: subscribe.isPending,
                disabled: !publicKey,
                onClick: () => subscribe.mutate(publicKey, { onSuccess: () => setKnown(true) }),
              }
        }
        actions={
          count
            ? [
                {
                  key: "test",
                  label: t("push.test"),
                  icon: <Send />,
                  onClick: () => test.mutate(),
                  disabled: test.isPending,
                },
              ]
            : []
        }
      >
        <p className={["text-secondary", styles.intro].join(" ")}>
          {t("push.intro")}
          <Help title={t("push.title")} as="text">
            <p>{t("push.introMore")}</p>
            <p>{t("push.note")}</p>
          </Help>
        </p>
      </SettingsHeader>
      {test.data && (
        <Notice kind={test.data.sent > 0 ? "success" : "attention"}>
          {t("push.tested", { sent: test.data.sent, failed: test.data.failed })}
        </Notice>
      )}
      {failure && <Notice kind="error">{failure.message}</Notice>}
    </div>
  );
}
