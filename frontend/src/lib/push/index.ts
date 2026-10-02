import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type PushStatus = components["schemas"]["PushStatusOut"];
export const pushKey = ["push"] as const;

/** Whether this browser can take push messages at all; the server may still have them off. */
export function pushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    window.isSecureContext &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

/** The service worker, once it runs; a worker that never starts must not hang the page. */
async function readyWorker(): Promise<ServiceWorkerRegistration> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const gaveUp = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error("The app's service worker is not running.")), 10_000);
  });
  try {
    return await Promise.race([navigator.serviceWorker.ready, gaveUp]);
  } finally {
    clearTimeout(timer);
  }
}

export function usePushStatus(enabled = true) {
  return useQuery({
    queryKey: pushKey,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/push");
      if (!data) throw new Error(errorMessage(error, "Notifications could not be checked."));
      return data;
    },
    enabled,
  });
}

function keyBytes(base64url: string): Uint8Array<ArrayBuffer> {
  const padded =
    base64url.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (base64url.length % 4)) % 4);
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return bytes;
}

/** This device's subscription, if the browser holds one. */
export async function currentSubscription(): Promise<PushSubscription | null> {
  if (!pushSupported()) return null;
  const registration = await navigator.serviceWorker.getRegistration();
  if (!registration) return null;
  return registration.pushManager.getSubscription();
}

/** Ask the browser for permission and a subscription, then tell the server about this device. */
export function useSubscribeDevice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (publicKey: string) => {
      if ((await Notification.requestPermission()) !== "granted") {
        throw new Error("The browser did not allow notifications.");
      }
      const registration = await readyWorker();
      const subscription =
        (await registration.pushManager.getSubscription()) ??
        (await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: keyBytes(publicKey),
        }));
      const json = subscription.toJSON();
      const { data, error } = await api.POST("/api/push/subscriptions", {
        body: {
          endpoint: json.endpoint ?? subscription.endpoint,
          keys: { p256dh: json.keys?.p256dh ?? "", auth: json.keys?.auth ?? "" },
        },
      });
      if (!data) throw new Error(errorMessage(error, "This device could not be subscribed."));
      return data;
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: pushKey }),
  });
}

export function useUnsubscribeDevice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const subscription = await currentSubscription();
      if (!subscription) return;
      const { response, error } = await api.DELETE("/api/push/subscriptions", {
        body: { endpoint: subscription.endpoint },
      });
      if (!response.ok) throw new Error(errorMessage(error, "This device could not be unsubscribed."));
      await subscription.unsubscribe();
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: pushKey }),
  });
}

export function useTestPush() {
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/push/test");
      if (!data) throw new Error(errorMessage(error, "The test message could not be sent."));
      return data;
    },
  });
}
