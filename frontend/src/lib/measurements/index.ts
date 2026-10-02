import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type ImageScale = components["schemas"]["ImageScaleOut"];
export type ScaleReference = components["schemas"]["ScaleReferenceOut"];
export type Measurement = components["schemas"]["MeasurementOut"];
export type MeasurementIn = components["schemas"]["MeasurementIn"];
export type MeasurementPreview = components["schemas"]["MeasurementPreview"];
export type Fit = components["schemas"]["FitOut"];
export type Point = { x: number; y: number };
export type Circle = { cx: number; cy: number; r: number };

export const COINS = [
  { id: "1c", mm: 16.25 },
  { id: "2c", mm: 18.75 },
  { id: "5c", mm: 21.25 },
  { id: "10c", mm: 19.75 },
  { id: "20c", mm: 22.25 },
  { id: "50c", mm: 24.25 },
  { id: "1e", mm: 23.25 },
  { id: "2e", mm: 25.75 },
] as const;
export type Denomination = (typeof COINS)[number]["id"];

const scaleKey = (imageId: string) => ["images", imageId, "scale"] as const;
const visitMeasurementsKey = (observationId: string) =>
  ["observations", observationId, "measurements"] as const;

export function useImageScale(imageId: string) {
  return useQuery({
    queryKey: scaleKey(imageId),
    queryFn: async () => {
      const { data, error } = await api.GET("/api/images/{image_id}/scale", {
        params: { path: { image_id: imageId } },
      });
      if (!data) throw new Error(errorMessage(error, "The scale could not be loaded."));
      return data;
    },
    enabled: imageId !== "",
    // The card search runs in the background after the upload.
    refetchInterval: (query) => (query.state.data && !query.state.data.card_checked ? 2000 : false),
  });
}

export function useFit(imageId: string) {
  return useMutation({
    mutationFn: async (body: { x: number; y: number; target: "coin" | "lesion" }) => {
      const { data, error } = await api.POST("/api/images/{image_id}/fit", {
        params: { path: { image_id: imageId } },
        body,
      });
      if (!data) throw new Error(errorMessage(error, "Nothing to fit was found there."));
      return data;
    },
  });
}

export function useAddScaleReference(imageId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (
      body:
        | { kind: "coin"; cx: number; cy: number; r: number; denomination: Denomination }
        | { kind: "manual"; x1: number; y1: number; x2: number; y2: number; length_mm: number },
    ) => {
      const { data, error } = await api.POST("/api/images/{image_id}/scale-references", {
        params: { path: { image_id: imageId } },
        body,
      });
      if (!data) throw new Error(errorMessage(error, "The scale could not be saved."));
      return data;
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: scaleKey(imageId) }),
  });
}

export async function previewMeasurement(
  observationId: string,
  body: MeasurementIn,
): Promise<MeasurementPreview> {
  const { data, error } = await api.POST("/api/observations/{observation_id}/measurements/preview", {
    params: { path: { observation_id: observationId } },
    body,
  });
  if (!data) throw new Error(errorMessage(error, "The size could not be computed."));
  return data;
}

export function useCreateMeasurement(observationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: MeasurementIn) => {
      const { data, error } = await api.POST("/api/observations/{observation_id}/measurements", {
        params: { path: { observation_id: observationId } },
        body,
      });
      if (!data) throw new Error(errorMessage(error, "The measurement could not be saved."));
      return data;
    },
    onSuccess: () => void queryClient.invalidateQueries(),
  });
}

export function useVisitMeasurements(observationId: string) {
  return useQuery({
    queryKey: visitMeasurementsKey(observationId),
    queryFn: async () => {
      const { data, error } = await api.GET("/api/observations/{observation_id}/measurements", {
        params: { path: { observation_id: observationId } },
      });
      if (!data) throw new Error(errorMessage(error, "The measurements could not be loaded."));
      return data;
    },
    enabled: observationId !== "",
  });
}

export function useLesionMeasurements(lesionId: string) {
  return useQuery({
    queryKey: ["lesions", lesionId, "measurements"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/lesions/{lesion_id}/measurements", {
        params: { path: { lesion_id: lesionId } },
      });
      if (!data) throw new Error(errorMessage(error, "The measurements could not be loaded."));
      return data;
    },
    enabled: lesionId !== "",
  });
}

export function useDeleteMeasurement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (measurementId: string) => {
      const { error, response } = await api.DELETE("/api/measurements/{measurement_id}", {
        params: { path: { measurement_id: measurementId } },
      });
      if (!response.ok) throw new Error(errorMessage(error, "The measurement could not be deleted."));
    },
    onSuccess: () => void queryClient.invalidateQueries(),
  });
}

/** "4.4 ± 0.3 mm", or "4.4 mm" when the person chose not to see uncertainty in the app. */
export function formatMm(
  value: number,
  sigma: number | null,
  locale: string,
  showUncertainty: boolean,
): string {
  const format = new Intl.NumberFormat(locale, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  if (!showUncertainty || sigma === null) return `${format.format(value)} mm`;
  return `${format.format(value)} ± ${format.format(Math.max(sigma, 0.1))} mm`;
}

export function formatDelta(delta: number, sigma: number, locale: string, showUncertainty: boolean): string {
  const format = new Intl.NumberFormat(locale, {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
    signDisplay: "always",
  });
  const plain = new Intl.NumberFormat(locale, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  return showUncertainty
    ? `${format.format(delta)} ± ${plain.format(Math.max(sigma, 0.1))} mm`
    : `${format.format(delta)} mm`;
}
