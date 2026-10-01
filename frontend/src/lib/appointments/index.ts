import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type AppointmentOut = components["schemas"]["AppointmentOut"];
export type ChecklistItem = components["schemas"]["ChecklistItem"];
type VisitReportIn = components["schemas"]["VisitReportIn"];

const appointmentKey = (id: string) => ["appointments", id] as const;

export function useAppointments(personId: string) {
  return useQuery({
    queryKey: ["persons", personId, "appointments"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/persons/{person_id}/appointments", {
        params: { path: { person_id: personId } },
      });
      if (!data) throw new Error(errorMessage(error, "The appointments could not be loaded."));
      return data;
    },
    enabled: personId !== "",
  });
}

export function useUpcomingAppointments() {
  return useQuery({
    queryKey: ["appointments", "upcoming"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/appointments/upcoming");
      if (!data) throw new Error(errorMessage(error, "The appointments could not be loaded."));
      return data;
    },
  });
}

export function useAppointment(id: string) {
  return useQuery({
    queryKey: appointmentKey(id),
    queryFn: async () => {
      const { data, error } = await api.GET("/api/appointments/{appointment_id}", {
        params: { path: { appointment_id: id } },
      });
      if (!data) throw new Error(errorMessage(error, "The appointment could not be loaded."));
      return data;
    },
    enabled: id !== "",
  });
}

export function useCreateAppointment(personId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: { date: string; notes: string | null }) => {
      const { data, error } = await api.POST("/api/persons/{person_id}/appointments", {
        params: { path: { person_id: personId } },
        body,
      });
      if (!data) throw new Error(errorMessage(error, "The appointment could not be saved."));
      return data;
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["appointments"] }),
  });
}

export function useUpdateAppointment(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: { date?: string; notes?: string | null }) => {
      const { data, error } = await api.PATCH("/api/appointments/{appointment_id}", {
        params: { path: { appointment_id: id } },
        body,
      });
      if (!data) throw new Error(errorMessage(error, "The appointment could not be saved."));
      return data;
    },
    onSuccess: () => void queryClient.invalidateQueries(),
  });
}

export function useDeleteAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { error, response } = await api.DELETE("/api/appointments/{appointment_id}", {
        params: { path: { appointment_id: id } },
      });
      if (!response.ok) throw new Error(errorMessage(error, "The appointment could not be deleted."));
    },
    onSuccess: () => void queryClient.invalidateQueries(),
  });
}

/** The appointment's report: the summary of every mark, then the record of each mark on the list. */
export function useVisitReport(id: string, personId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: VisitReportIn) => {
      const { data, error } = await api.POST("/api/appointments/{appointment_id}/report", {
        params: { path: { appointment_id: id } },
        body,
      });
      if (!data) throw new Error(errorMessage(error, "The report could not be requested."));
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: appointmentKey(id) });
      void queryClient.invalidateQueries({ queryKey: ["persons", personId, "reports"] });
    },
  });
}

/** Start a visit of one mark from the checklist; the caller goes to the visit to take the photos. */
export function useStartVisit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (lesionId: string) => {
      const { data, error } = await api.POST("/api/lesions/{lesion_id}/observations", {
        params: { path: { lesion_id: lesionId } },
        body: { captured_tz: Intl.DateTimeFormat().resolvedOptions().timeZone },
      });
      if (!data) throw new Error(errorMessage(error, "The visit could not be created."));
      return data;
    },
    onSuccess: () => void queryClient.invalidateQueries(),
  });
}

/** Whole days from today (local) to an ISO date: negative when it is past. */
export function daysUntil(isoDate: string, today: Date = new Date()): number {
  const [y, m, d] = isoDate.split("-").map(Number);
  const target = Date.UTC(y ?? 1970, (m ?? 1) - 1, d ?? 1);
  const now = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  return Math.round((target - now) / 86_400_000);
}
