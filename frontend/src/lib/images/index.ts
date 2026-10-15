import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type ImageOut = components["schemas"]["ImageOut"];
export type ImageRole = "overview" | "close_up" | "with_reference" | "other";
export const IMAGE_ROLES: ImageRole[] = ["close_up", "with_reference", "overview", "other"];

export type RenditionKind = "original" | "full" | "preview" | "thumb" | "normalised" | "normalised_thumb";

export function imageUrl(imageId: string, kind: RenditionKind): string {
  return `/api/images/${imageId}/${kind}`;
}

export function useDeleteImage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (imageId: string) => {
      const { error, response } = await api.DELETE("/api/images/{image_id}", {
        params: { path: { image_id: imageId } },
      });
      if (!response.ok) throw new Error(errorMessage(error, "The photo could not be deleted."));
    },
    // A photo belongs to a visit, which feeds the mark's thumbnail and the person's list: refresh everything.
    onSuccess: () => void queryClient.invalidateQueries(),
  });
}

/** The normalised view of a card photo (flat, upright, cropped to the card), once the server has made it. */
export function normalisedOf(image: Pick<ImageOut, "renditions">) {
  return image.renditions.find((rendition) => rendition.kind === "normalised") ?? null;
}
