import { create } from 'zustand';
import type { ContentFilters, ContentStatus } from '@/types';

interface ContentState {
  // Filters
  filters: ContentFilters;
  setFilters: (filters: ContentFilters) => void;
  updateFilter: <K extends keyof ContentFilters>(key: K, value: ContentFilters[K]) => void;
  clearFilters: () => void;

  // Selected content for detail view
  selectedContentId: number | null;
  setSelectedContent: (id: number | null) => void;

  // Editing state
  isEditing: boolean;
  editedText: string;
  setIsEditing: (editing: boolean) => void;
  setEditedText: (text: string) => void;

  // Quick filters
  quickFilter: 'all' | 'pending' | 'approved' | 'published';
  setQuickFilter: (filter: 'all' | 'pending' | 'approved' | 'published') => void;
}

const defaultFilters: ContentFilters = {
  status: ['pending_review'],
  project_id: undefined,
  opportunity_id: undefined,
};

export const useContentStore = create<ContentState>((set) => ({
  // Filters
  filters: defaultFilters,
  setFilters: (filters) => set({ filters }),
  updateFilter: (key, value) =>
    set((state) => ({
      filters: { ...state.filters, [key]: value },
    })),
  clearFilters: () => set({ filters: defaultFilters }),

  // Selected content
  selectedContentId: null,
  setSelectedContent: (id) => set({ selectedContentId: id, isEditing: false, editedText: '' }),

  // Editing state
  isEditing: false,
  editedText: '',
  setIsEditing: (editing) => set({ isEditing: editing }),
  setEditedText: (text) => set({ editedText: text }),

  // Quick filters
  quickFilter: 'pending',
  setQuickFilter: (filter) => {
    let newFilters: ContentFilters = {};

    switch (filter) {
      case 'pending':
        newFilters = { status: ['pending_review'] };
        break;
      case 'approved':
        newFilters = { status: ['approved'] };
        break;
      case 'published':
        newFilters = { status: ['published'] };
        break;
      default:
        newFilters = { status: ['draft', 'pending_review', 'approved', 'rejected'] };
    }

    set({ quickFilter: filter, filters: newFilters });
  },
}));
