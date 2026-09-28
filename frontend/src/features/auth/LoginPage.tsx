import { useTranslation } from "react-i18next";
import { Navigate } from "react-router";
import { useInstance, useLogin, useSession } from "@/lib/auth/session";
import { CredentialsForm } from "./CredentialsForm";

export function LoginPage() {
  const { t } = useTranslation();
  const session = useSession();
  const instance = useInstance();
  const login = useLogin();
  if (session.data) return <Navigate to="/" replace />;
  if (instance.data && !instance.data.claimed) return <Navigate to="/claim" replace />;
  return (
    <CredentialsForm
      title={t("auth.loginTitle")}
      submitLabel={t("auth.loginAction")}
      pending={login.isPending}
      error={login.error?.message}
      onSubmit={(credentials) => login.mutate(credentials)}
    />
  );
}
