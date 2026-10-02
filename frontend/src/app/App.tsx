import { BrowserRouter, Route, Routes } from "react-router";
import { AppointmentPage } from "@/features/appointments/AppointmentPage";
import { ClaimPage } from "@/features/auth/ClaimPage";
import { EvaluationPage } from "@/features/evaluation/EvaluationPage";
import { LabelPage } from "@/features/evaluation/LabelPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { RequireAuth } from "@/features/auth/RequireAuth";
import { ComparePage } from "@/features/compare/ComparePage";
import { LesionPage } from "@/features/lesions/LesionPage";
import { ObservationPage } from "@/features/lesions/ObservationPage";
import { MeasurePage } from "@/features/measure/MeasurePage";
import { HomePage } from "@/features/persons/HomePage";
import { PersonPage } from "@/features/persons/PersonPage";
import { SessionComparePage } from "@/features/sessions/SessionComparePage";
import { SessionPage } from "@/features/sessions/SessionPage";
import { ZonePage } from "@/features/sessions/ZonePage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { TrashPage } from "@/features/trash/TrashPage";
import { Shell } from "./Shell";

export function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/claim"
        element={
          <main>
            <ClaimPage />
          </main>
        }
      />
      <Route
        path="/login"
        element={
          <main>
            <LoginPage />
          </main>
        }
      />
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
        <Route path="lesions/:lesionId/compare" element={<ComparePage />} />
        <Route path="observations/:observationId" element={<ObservationPage />} />
        <Route path="observations/:observationId/measure/:imageId" element={<MeasurePage />} />
        <Route path="appointments/:appointmentId" element={<AppointmentPage />} />
        <Route path="sessions/:sessionId" element={<SessionPage />} />
        <Route path="sessions/:sessionId/zones/:zone" element={<ZonePage />} />
        <Route path="sessions/:sessionId/compare/:otherId" element={<SessionComparePage />} />
        <Route path="evaluation" element={<EvaluationPage />} />
        <Route path="evaluation/:imageId" element={<LabelPage />} />
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
