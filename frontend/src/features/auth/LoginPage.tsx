import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate } from "react-router";
import { Button } from "@/design-system/components/Button";
import { useInstance, useLogin, useSession } from "@/lib/auth/session";
import { CredentialsForm } from "./CredentialsForm";
import { SecondFactorForm } from "./SecondFactorForm";
import styles from "./auth.module.css";

export function LoginPage() {
  const { t } = useTranslation();
  const session = useSession();
  const instance = useInstance();
  const login = useLogin();
  const [codeStep, setCodeStep] = useState(false);
  if (session.data) return <Navigate to="/" replace />;
  if (instance.data?.auth_mode === "proxy") {
    return (
      <section className={styles.form}>
        <h1>{t("auth.proxyTitle")}</h1>
        <p className="text-secondary">{t("auth.proxyText")}</p>
        <div>
          <Button onClick={() => void session.refetch()} disabled={session.isFetching}>
            {t("auth.proxyRetry")}
          </Button>
        </div>
      </section>
    );
  }
  if (instance.data && !instance.data.claimed) return <Navigate to="/claim" replace />;
  if (codeStep) return <SecondFactorForm onBack={() => setCodeStep(false)} />;
  return (
    <CredentialsForm
      title={t("auth.loginTitle")}
      submitLabel={t("auth.loginAction")}
      pending={login.isPending}
      error={login.error?.message}
      onSubmit={(credentials) =>
        login.mutate(credentials, {
          onSuccess: (answer) => {
            if (answer.second_factor_required) setCodeStep(true);
          },
        })
      }
    />
  );
}
