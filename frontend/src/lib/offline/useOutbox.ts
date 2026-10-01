import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { onOutboxChange, queuedVisits, syncOutbox, type QueuedVisit } from "./outbox";

/** The account's queued visits, uploaded whenever the device is back online, visible or focused. */
export function useOutbox(userId: string | undefined) {
  const queryClient = useQueryClient();
  const [visits, setVisits] = useState<QueuedVisit[]>([]);
  const [online, setOnline] = useState(typeof navigator === "undefined" ? true : navigator.onLine);

  useEffect(() => {
    if (!userId) return;
    let alive = true;
    const refresh = () => void queuedVisits(userId).then((list) => alive && setVisits(list));
    const sync = () => {
      if (!navigator.onLine) return;
      void syncOutbox(userId).then((done) => {
        if (done > 0) void queryClient.invalidateQueries();
        refresh();
      });
    };
    const goOnline = () => {
      setOnline(true);
      sync();
    };
    const goOffline = () => setOnline(false);
    const visible = () => document.visibilityState === "visible" && sync();
    refresh();
    sync();
    const stop = onOutboxChange(refresh);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    window.addEventListener("focus", sync);
    document.addEventListener("visibilitychange", visible);
    const timer = window.setInterval(sync, 30_000);
    return () => {
      alive = false;
      stop();
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
      window.removeEventListener("focus", sync);
      document.removeEventListener("visibilitychange", visible);
      window.clearInterval(timer);
    };
  }, [userId, queryClient]);

  return {
    visits,
    online,
    syncNow: () => userId && void syncOutbox(userId).then(() => void queryClient.invalidateQueries()),
  };
}
