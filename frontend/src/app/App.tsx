import { BrowserRouter, Route, Routes } from "react-router";
import { ClaimPage } from "@/features/auth/ClaimPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { RequireAuth } from "@/features/auth/RequireAuth";
import { LesionPage } from "@/features/lesions/LesionPage";
import { ObservationPage } from "@/features/lesions/ObservationPage";
import { MeasurePage } from "@/features/measure/MeasurePage";
import { HomePage } from "@/features/persons/HomePage";
import { PersonPage } from "@/features/persons/PersonPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { TrashPage } from "@/features/trash/TrashPage";
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
        <Route path="lesions/:lesionId" element={<LesionPage />} />
        <Route path="observations/:observationId" element={<ObservationPage />} />
        <Route path="observations/:observationId/measure/:imageId" element={<MeasurePage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="trash" element={<TrashPage />} />
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
