import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import i18n from "@/lib/i18n";
import { applyTheme } from "@/lib/theme";

export type SessionInfo = components["schemas"]["SessionOut"];
export type UserOut = components["schemas"]["UserOut"];
export type Credentials = components["schemas"]["Credentials"];
export type InstanceStatus = components["schemas"]["InstanceStatus"];
export type LoginOut = components["schemas"]["LoginOut"];
export type SecondFactorIn = components["schemas"]["SecondFactorIn"];

export const sessionKey = ["session"] as const;
export const instanceKey = ["instance"] as const;

/** Apply the preferences stored with the account: language and theme follow the person, not the browser. */
export function applyUserPreferences(user: UserOut): void {
  if (user.language !== i18n.resolvedLanguage) void i18n.changeLanguage(user.language);
  applyTheme(user.theme);
}

export function useInstance() {
  return useQuery({
    queryKey: instanceKey,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/auth/instance");
      if (!data) throw new Error(errorMessage(error, "The server did not answer."));
      return data;
    },
    staleTime: 60_000,
  });
}

export function useSession() {
  return useQuery({
    queryKey: sessionKey,
    queryFn: async (): Promise<SessionInfo | null> => {
      const { data, response } = await api.GET("/api/auth/session");
      if (response.status === 401) return null;
      if (!data) throw new Error("The server did not answer.");
      applyUserPreferences(data.user);
      return data;
    },
    staleTime: 60_000,
    retry: false,
  });
}

function useSessionMutation<Input>(request: (input: Input) => Promise<SessionInfo>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: request,
    onSuccess: (data) => {
      applyUserPreferences(data.user);
      queryClient.setQueryData(sessionKey, data);
      void queryClient.invalidateQueries({ queryKey: instanceKey });
    },
  });
}

/** The password; when the account has a second factor, the answer asks for its code next. */
export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (credentials: Credentials): Promise<LoginOut> => {
      const { data, error } = await api.POST("/api/auth/login", { body: credentials });
      if (!data) throw new Error(errorMessage(error, "Wrong username or password."));
      return data;
    },
    onSuccess: (data) => {
      if (!data.session) return;
      applyUserPreferences(data.session.user);
      queryClient.setQueryData(sessionKey, data.session);
      void queryClient.invalidateQueries({ queryKey: instanceKey });
    },
  });
}

/** The code from the authenticator, or a recovery code, after the password was accepted. */
export function useSecondFactor() {
  return useSessionMutation(async (body: SecondFactorIn) => {
    const { data, error } = await api.POST("/api/auth/second-factor", { body });
    if (!data) throw new Error(errorMessage(error, "Wrong code."));
    return data;
  });
}

export function useClaim() {
  return useSessionMutation(async (credentials: Credentials) => {
    const { data, error } = await api.POST("/api/auth/claim", { body: credentials });
    if (!data) throw new Error(errorMessage(error, "The instance could not be claimed."));
    return data;
  });
}

/** Signing out leaves nothing of this account on the device: queued visits and cached responses go. */
async function forgetDevice(): Promise<void> {
  const { clearOutbox } = await import("@/lib/offline/outbox");
  await clearOutbox().catch(() => undefined);
  if (typeof caches !== "undefined") {
    for (const name of ["api", "photos"]) await caches.delete(name).catch(() => false);
  }
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.POST("/api/auth/logout");
    },
    onSettled: () => {
      const instance = queryClient.getQueryData<InstanceStatus>(instanceKey);
      queryClient.setQueryData(sessionKey, null);
      queryClient.clear();
      void forgetDevice();
      // Behind a single sign-on proxy, signing out here alone would sign straight back in.
      if (instance?.logout_url) window.location.assign(instance.logout_url);
    },
  });
}

export function useUpdateMe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: components["schemas"]["UserUpdateMe"]) => {
      const { data, error } = await api.PATCH("/api/auth/me", { body });
      if (!data) throw new Error(errorMessage(error, "The change could not be saved."));
      return data;
    },
    onSuccess: (user) => {
      applyUserPreferences(user);
      queryClient.setQueryData(sessionKey, (old: SessionInfo | null | undefined) =>
        old ? { ...old, user } : old,
      );
    },
  });
}
