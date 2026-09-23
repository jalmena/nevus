import { BrowserRouter, Route, Routes } from "react-router";
import { ClaimPage } from "@/features/auth/ClaimPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { RequireAuth } from "@/features/auth/RequireAuth";
import { HomePage } from "@/features/persons/HomePage";
import { PersonPage } from "@/features/persons/PersonPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { Shell } from "./Shell";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/claim" element={<ClaimPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <Shell />
          </RequireAuth>
        }
      >
        <Route index element={<HomePage />} />
        <Route path="persons/:personId" element={<PersonPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
