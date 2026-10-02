import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { sessionKey } from "@/lib/auth/session";
import { useSudo, withSudo } from "@/lib/sudo/SudoProvider";

export type TotpStatus = components["schemas"]["TotpStatusOut"];
export type TotpSetup = components["schemas"]["TotpSetupOut"];
export const totpKey = ["totp"] as const;

export function useTotpStatus(enabled: boolean) {
  return useQuery({
    queryKey: totpKey,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/auth/totp");
      if (!data) throw new Error(errorMessage(error, "The second factor could not be checked."));
      return data;
    },
    enabled,
  });
}

/** A new secret to put in the authenticator; the factor turns on with the first code from it. */
export function useTotpSetup() {
  const ask = useSudo();
  return useMutation({
    mutationFn: async (): Promise<TotpSetup> => {
      const { data, error } = await withSudo(ask, () => api.POST("/api/auth/totp/setup"));
      if (!data) throw new Error(errorMessage(error, "The second factor could not be set up."));
      return data;
    },
  });
}

function useTotpChange<Input, Output>(run: (input: Input) => Promise<Output>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: run,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: totpKey });
      void queryClient.invalidateQueries({ queryKey: sessionKey });
    },
  });
}

export function useTotpEnable() {
  const ask = useSudo();
  return useTotpChange(async ({ code }: { code: string }) => {
    const { data, error } = await withSudo(ask, () =>
      api.POST("/api/auth/totp/enable", { body: { code: code.replace(/\s+/g, "") } }),
    );
    if (!data) throw new Error(errorMessage(error, "That code does not match."));
    return data.recovery_codes;
  });
}

export function useTotpDisable() {
  const ask = useSudo();
  return useTotpChange(async () => {
    const { response, error } = await withSudo(ask, () => api.DELETE("/api/auth/totp"));
    if (!response.ok) throw new Error(errorMessage(error, "The second factor could not be turned off."));
  });
}

export function useNewRecoveryCodes() {
  const ask = useSudo();
  return useTotpChange(async () => {
    const { data, error } = await withSudo(ask, () => api.POST("/api/auth/totp/recovery-codes"));
    if (!data) throw new Error(errorMessage(error, "New recovery codes could not be made."));
    return data.recovery_codes;
  });
}
