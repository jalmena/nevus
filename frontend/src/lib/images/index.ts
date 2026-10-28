import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type ImageOut = components["schemas"]["ImageOut"];
export type ImageRole = "overview" | "close_up" | "with_reference" | "other";
export const IMAGE_ROLES: ImageRole[] = ["close_up", "with_reference", "overview", "other"];

export type RenditionKind =
  "original" | "full" | "preview" | "thumb" | "normalised" | "normalised_thumb" | "mark" | "mark_thumb";

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

/** The mark in the card's window (flat, upright, no card in view), once the server has cut it. */
export function markOf(image: Pick<ImageOut, "renditions">) {
  return image.renditions.find((rendition) => rendition.kind === "mark") ?? null;
}

/**
 * The thumbnail to show for a photo whose record is at hand: the mark in its window when the server has cut
 * it, else the normalised card, else the plain thumbnail. Naming the kind in the URL means the picture
 * changes the moment the record does; the `thumb` alias serves the places that only know an id.
 */
export function thumbOf(image: Pick<ImageOut, "id" | "renditions">): string {
  const kinds = new Set(image.renditions.map((rendition) => rendition.kind));
  const kind: RenditionKind = kinds.has("mark_thumb")
    ? "mark_thumb"
    : kinds.has("normalised_thumb")
      ? "normalised_thumb"
      : "thumb";
  return imageUrl(image.id, kind);
}

/** Whether the background analyses that can still change how a photo is shown may be running. */
export function stillAnalysing(
  image: Pick<ImageOut, "quality_checked_at" | "analysed_at" | "created_at">,
  now = Date.now(),
): boolean {
  if (image.quality_checked_at && image.analysed_at) return false;
  // A photo whose analysis never settles (a job that failed for good) must not keep a page polling forever.
  return now - new Date(image.created_at).getTime() < 10 * 60 * 1000;
}
