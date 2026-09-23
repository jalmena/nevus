import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type PersonOut = components["schemas"]["PersonOut"];
export type PersonIn = components["schemas"]["PersonIn"];

export const personsKey = ["persons"] as const;

export function usePersons() {
  return useQuery({
    queryKey: personsKey,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/persons");
      if (!data) throw new Error(errorMessage(error, "The persons could not be loaded."));
      return data;
    },
  });
}

export function usePerson(personId: string) {
  return useQuery({
    queryKey: [...personsKey, personId],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/persons/{person_id}", {
        params: { path: { person_id: personId } },
      });
      if (!data) throw new Error(errorMessage(error, "This person could not be loaded."));
      return data;
    },
  });
}

export function useCreatePerson() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: PersonIn) => {
      const { data, error } = await api.POST("/api/persons", { body });
      if (!data) throw new Error(errorMessage(error, "The person could not be created."));
      return data;
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: personsKey }),
  });
}
