import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { useSudo, withSudo } from "@/lib/sudo/SudoProvider";

export type EmailSettings = components["schemas"]["EmailSettingsOut"];
export type EmailSettingsIn = components["schemas"]["EmailSettingsIn"];

export function useEmailSettings(enabled: boolean) {
  return useQuery({
    queryKey: ["admin", "email"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/admin/email");
      if (!data) throw new Error(errorMessage(error, "The email settings could not be loaded."));
      return data;
    },
    enabled,
  });
}

export function useSaveEmailSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: EmailSettingsIn) => {
      const { data, error } = await api.PUT("/api/admin/email", { body });
      if (!data) throw new Error(errorMessage(error, "The email settings could not be saved."));
      return data;
    },
    onSuccess: (data) => queryClient.setQueryData(["admin", "email"], data),
  });
}

export function useTestEmail() {
  return useMutation({
    mutationFn: async (to: string) => {
      const { error, response } = await api.POST("/api/admin/email/test", { body: { to } });
      if (!response.ok) throw new Error(errorMessage(error, "The test message could not be sent."));
    },
  });
}

export function useInstanceSettings(enabled: boolean) {
  return useQuery({
    queryKey: ["admin", "instance"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/admin/instance");
      if (!data) throw new Error(errorMessage(error, "The instance settings could not be loaded."));
      return data;
    },
    enabled,
  });
}

export function useSaveInstanceSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: components["schemas"]["InstanceOut"]) => {
      const { data, error } = await api.PUT("/api/admin/instance", { body });
      if (!data) throw new Error(errorMessage(error, "The instance settings could not be saved."));
      return data;
    },
    onSuccess: (data) => queryClient.setQueryData(["admin", "instance"], data),
  });
}

// --- accounts ------------------------------------------------------------------------------------

export type UserOut = components["schemas"]["UserOut"];
export const usersKey = ["users"] as const;

export function useUsers() {
  return useQuery({
    queryKey: usersKey,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/users");
      if (!data) throw new Error(errorMessage(error, "The accounts could not be loaded."));
      return data;
    },
  });
}

function useUsersMutation<Input>(run: (input: Input) => Promise<void>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: run,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: usersKey }),
  });
}

export function useCreateUser() {
  return useUsersMutation(async (body: components["schemas"]["UserCreate"]) => {
    const { response, error } = await api.POST("/api/users", { body });
    if (!response.ok) throw new Error(errorMessage(error, "The account could not be created."));
  });
}

export function useSetUserEnabled() {
  return useUsersMutation(async ({ id, enabled }: { id: string; enabled: boolean }) => {
    const params = { params: { path: { user_id: id } } };
    const { response, error } = enabled
      ? await api.POST("/api/users/{user_id}/enable", params)
      : await api.POST("/api/users/{user_id}/disable", params);
    if (!response.ok) throw new Error(errorMessage(error, "The account could not be changed."));
  });
}

export function useResetUserPassword() {
  return useUsersMutation(async ({ id, password }: { id: string; password: string }) => {
    const { response, error } = await api.POST("/api/users/{user_id}/password", {
      params: { path: { user_id: id } },
      body: { new_password: password },
    });
    if (!response.ok) throw new Error(errorMessage(error, "The password could not be set."));
  });
}

/** For a member who lost the authenticator; asks for the administrator's password again. */
export function useResetUserSecondFactor() {
  const ask = useSudo();
  return useUsersMutation(async (id: string) => {
    const { response, error } = await withSudo(ask, () =>
      api.DELETE("/api/users/{user_id}/totp", { params: { path: { user_id: id } } }),
    );
    if (!response.ok) throw new Error(errorMessage(error, "The second factor could not be turned off."));
  });
}

// --- backups -------------------------------------------------------------------------------------

export type BackupStatus = components["schemas"]["BackupStatusOut"];
export const backupsKey = ["admin", "backups"] as const;

/** The backups' state; checked again every few seconds while a backup or a verification is queued. */
export function useBackupStatus(enabled: boolean) {
  return useQuery({
    queryKey: backupsKey,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/admin/backups");
      if (!data) throw new Error(errorMessage(error, "The backups could not be checked."));
      return data;
    },
    enabled,
    refetchInterval: (query) =>
      query.state.data?.backup_queued || query.state.data?.verification_queued ? 5000 : false,
  });
}

function useBackupAction(path: "/api/admin/backups/run" | "/api/admin/backups/verify", failure: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { response, error } = await api.POST(path);
      if (!response.ok) throw new Error(errorMessage(error, failure));
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: backupsKey }),
  });
}

export const useBackupNow = () =>
  useBackupAction("/api/admin/backups/run", "The backup could not be started.");
export const useVerifyBackupNow = () =>
  useBackupAction("/api/admin/backups/verify", "The verification could not be started.");
