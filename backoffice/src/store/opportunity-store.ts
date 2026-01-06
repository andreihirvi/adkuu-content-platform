import { create } from 'zustand';
import type { OpportunityFilters, UrgencyLevel, OpportunityStatus } from '@/types';

interface OpportunityState {
  // Filters
  filters: OpportunityFilters;
  setFilters: (filters: OpportunityFilters) => void;
  updateFilter: <K extends keyof OpportunityFilters>(key: K, value: OpportunityFilters[K]) => void;
  clearFilters: () => void;

  // Selected items for bulk actions
  selectedIds: number[];
  toggleSelected: (id: number) => void;
  selectAll: (ids: number[]) => void;
  clearSelection: () => void;

  // View preferences
  selectedOpportunityId: number | null;
  setSelectedOpportunity: (id: number | null) => void;

  // Quick filters
  quickFilter: 'all' | 'urgent' | 'new' | 'queued';
  setQuickFilter: (filter: 'all' | 'urgent' | 'new' | 'queued') => void;
}

const defaultFilters: OpportunityFilters = {
  status: ['new', 'queued'],
  urgency_level: undefined,
  project_id: undefined,
  subreddit: undefined,
  min_score: undefined,
};

export const useOpportunityStore = create<OpportunityState>((set, get) => ({
  // Filters
  filters: defaultFilters,
  setFilters: (filters) => set({ filters }),
  updateFilter: (key, value) =>
    set((state) => ({
      filters: { ...state.filters, [key]: value },
    })),
  clearFilters: () => set({ filters: defaultFilters }),

  // Selected items
  selectedIds: [],
  toggleSelected: (id) =>
    set((state) => ({
      selectedIds: state.selectedIds.includes(id)
        ? state.selectedIds.filter((i) => i !== id)
        : [...state.selectedIds, id],
    })),
  selectAll: (ids) => set({ selectedIds: ids }),
  clearSelection: () => set({ selectedIds: [] }),

  // View preferences
  selectedOpportunityId: null,
  setSelectedOpportunity: (id) => set({ selectedOpportunityId: id }),

  // Quick filters
  quickFilter: 'all',
  setQuickFilter: (filter) => {
    let newFilters: OpportunityFilters = { ...defaultFilters };

    switch (filter) {
      case 'urgent':
        newFilters = {
          ...newFilters,
          urgency_level: ['critical', 'high'],
          status: ['new', 'queued'],
        };
        break;
      case 'new':
        newFilters = {
          ...newFilters,
          status: ['new'],
        };
        break;
      case 'queued':
        newFilters = {
          ...newFilters,
          status: ['queued', 'in_progress'],
        };
        break;
      default:
        newFilters = {
          status: ['new', 'queued', 'in_progress'],
        };
    }

    set({ quickFilter: filter, filters: newFilters });
  },
}));
