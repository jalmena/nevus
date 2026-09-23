import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type ImageOut = components["schemas"]["ImageOut"];
export type ImageRole = "overview" | "close_up" | "with_reference" | "other";

export const imagesKey = (personId: string) => ["persons", personId, "images"] as const;

export function useImages(personId: string) {
  return useQuery({
    queryKey: imagesKey(personId),
    queryFn: async () => {
      const { data, error } = await api.GET("/api/persons/{person_id}/images", {
        params: { path: { person_id: personId } },
      });
      if (!data) throw new Error(errorMessage(error, "The photos could not be loaded."));
      return data;
    },
  });
}

export function imageUrl(imageId: string, kind: "original" | "full" | "preview" | "thumb"): string {
  return `/api/images/${imageId}/${kind}`;
}

export function useUploadImage(personId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ file, role }: { file: File; role: ImageRole }) => {
      const body = new FormData();
      body.append("file", file, file.name);
      body.append("role", role);
      body.append("modality", "camera");
      body.append("captured_tz", Intl.DateTimeFormat().resolvedOptions().timeZone);
      const response = await fetch(`/api/persons/${personId}/images`, {
        method: "POST",
        body,
        credentials: "same-origin",
      });
      const payload: unknown = await response.json().catch(() => null);
      if (!response.ok) throw new Error(errorMessage(payload, "The photo could not be uploaded."));
      return payload as ImageOut;
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: imagesKey(personId) }),
  });
}

export function useDeleteImage(personId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (imageId: string) => {
      const { error, response } = await api.DELETE("/api/images/{image_id}", {
        params: { path: { image_id: imageId } },
      });
      if (!response.ok) throw new Error(errorMessage(error, "The photo could not be deleted."));
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: imagesKey(personId) }),
  });
}
