import { lazy, type ComponentType } from "react";
import { BrowserRouter, Route, Routes } from "react-router";
import { ClaimPage } from "@/features/auth/ClaimPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { RequireAuth } from "@/features/auth/RequireAuth";
import { HomePage } from "@/features/persons/HomePage";
import { Shell } from "./Shell";

/** A page that loads when it is first opened, so the first paint carries only the home page. */
function page<Name extends string>(load: () => Promise<Record<Name, ComponentType>>, name: Name) {
  return lazy(() => load().then((module) => ({ default: module[name] })));
}

const PersonPage = page(() => import("@/features/persons/PersonPage"), "PersonPage");
const LesionPage = page(() => import("@/features/lesions/LesionPage"), "LesionPage");
const ObservationPage = page(() => import("@/features/lesions/ObservationPage"), "ObservationPage");
const ComparePage = page(() => import("@/features/compare/ComparePage"), "ComparePage");
const MeasurePage = page(() => import("@/features/measure/MeasurePage"), "MeasurePage");
const AppointmentPage = page(() => import("@/features/appointments/AppointmentPage"), "AppointmentPage");
const SessionPage = page(() => import("@/features/sessions/SessionPage"), "SessionPage");
const ZonePage = page(() => import("@/features/sessions/ZonePage"), "ZonePage");
const SessionComparePage = page(() => import("@/features/sessions/SessionComparePage"), "SessionComparePage");
const EvaluationPage = page(() => import("@/features/evaluation/EvaluationPage"), "EvaluationPage");
const LabelPage = page(() => import("@/features/evaluation/LabelPage"), "LabelPage");
const SettingsPage = page(() => import("@/features/settings/SettingsPage"), "SettingsPage");
const TrashPage = page(() => import("@/features/trash/TrashPage"), "TrashPage");

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
