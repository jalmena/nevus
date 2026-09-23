import type { ReactNode } from "react";
import { Navigate } from "react-router";
import { useInstance, useSession } from "@/lib/auth/session";

/** Sends visitors to the claim page on a fresh instance and to the login page otherwise. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const session = useSession();
  const instance = useInstance();
  if (session.isPending || instance.isPending) return <p className="text-secondary">…</p>;
  if (!session.data)
    return <Navigate to={instance.data && !instance.data.claimed ? "/claim" : "/login"} replace />;
  return <>{children}</>;
}
