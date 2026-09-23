import { useTranslation } from "react-i18next";
import { Navigate } from "react-router";
import { useClaim, useInstance, useSession } from "@/lib/auth/session";
import { CredentialsForm } from "./CredentialsForm";

/** First run: the first account becomes the administrator. Redirects are derived from state, never from callbacks. */
export function ClaimPage() {
  const { t } = useTranslation();
  const session = useSession();
  const instance = useInstance();
  const claim = useClaim();
  if (session.data) return <Navigate to="/" replace />;
  if (instance.data?.claimed) return <Navigate to="/login" replace />;
  return (
    <CredentialsForm
      title={t("auth.claimTitle")}
      intro={t("auth.claimIntro")}
      submitLabel={t("auth.claimAction")}
      confirm
      pending={claim.isPending}
      error={claim.error?.message}
      onSubmit={(credentials) => claim.mutate(credentials)}
    />
  );
}
