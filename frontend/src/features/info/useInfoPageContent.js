import { useMemo } from "react";
import {
  teamMembers,
  teamDescription,
  advantagesList,
  techStackList,
  projectAdvantagesTitle,
} from "./content";

export function useInfoPageContent() {
  return useMemo(
    () => ({
      heroDescription: teamDescription,
      teamMembers,
      advantagesList,
      techStackList,
      projectAdvantagesTitle,
    }),
    [],
  );
}
