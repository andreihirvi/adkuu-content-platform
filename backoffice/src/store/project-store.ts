import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Project } from '@/types';

interface ProjectState {
  // Selected project for filtering
  selectedProjectId: number | null;
  setSelectedProject: (id: number | null) => void;

  // Projects cache
  projects: Project[];
  setProjects: (projects: Project[]) => void;

  // Helpers
  getProject: (id: number) => Project | undefined;
  getSelectedProject: () => Project | undefined;
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set, get) => ({
      selectedProjectId: null,
      setSelectedProject: (id) => set({ selectedProjectId: id }),

      projects: [],
      setProjects: (projects) => set({ projects }),

      getProject: (id) => get().projects.find((p) => p.id === id),
      getSelectedProject: () => {
        const { selectedProjectId, projects } = get();
        return selectedProjectId ? projects.find((p) => p.id === selectedProjectId) : undefined;
      },
    }),
    {
      name: 'project-store',
      partialize: (state) => ({
        selectedProjectId: state.selectedProjectId,
      }),
    }
  )
);
