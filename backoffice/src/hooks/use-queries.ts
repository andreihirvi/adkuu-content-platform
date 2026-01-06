import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type {
  Project,
  Opportunity,
  GeneratedContent,
  RedditAccount,
  OpportunityFilters,
  ContentFilters,
} from '@/types';

// Query Keys
export const queryKeys = {
  dashboard: ['dashboard'] as const,
  projects: ['projects'] as const,
  project: (id: number) => ['projects', id] as const,
  accounts: ['accounts'] as const,
  account: (id: number) => ['accounts', id] as const,
  opportunities: (filters?: OpportunityFilters, page?: number) =>
    ['opportunities', filters, page] as const,
  opportunity: (id: number) => ['opportunities', id] as const,
  contents: (filters?: ContentFilters, page?: number) =>
    ['contents', filters, page] as const,
  content: (id: number) => ['contents', id] as const,
  analytics: (projectId?: number, dateRange?: { start: string; end: string }) =>
    ['analytics', projectId, dateRange] as const,
  subredditConfigs: (projectId: number) => ['subredditConfigs', projectId] as const,
};

// Dashboard
export function useDashboardStats() {
  return useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: () => apiClient.getDashboardStats(),
    refetchInterval: 60000, // Refresh every minute
  });
}

// Projects
export function useProjects() {
  return useQuery({
    queryKey: queryKeys.projects,
    queryFn: () => apiClient.getProjects(),
  });
}

export function useProject(id: number) {
  return useQuery({
    queryKey: queryKeys.project(id),
    queryFn: () => apiClient.getProject(id),
    enabled: !!id,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (project: Partial<Project>) => apiClient.createProject(project),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.projects });
    },
  });
}

export function useUpdateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Project> }) =>
      apiClient.updateProject(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.projects });
      queryClient.invalidateQueries({ queryKey: queryKeys.project(id) });
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiClient.deleteProject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.projects });
    },
  });
}

// Reddit Accounts
export function useRedditAccounts() {
  return useQuery({
    queryKey: queryKeys.accounts,
    queryFn: () => apiClient.getRedditAccounts(),
  });
}

export function useRedditAccount(id: number) {
  return useQuery({
    queryKey: queryKeys.account(id),
    queryFn: () => apiClient.getRedditAccount(id),
    enabled: !!id,
  });
}

export function useInitiateRedditOAuth() {
  return useMutation({
    mutationFn: () => apiClient.initiateRedditOAuth(),
  });
}

export function useDisconnectAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiClient.disconnectRedditAccount(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.accounts });
    },
  });
}

export function useRefreshAccountHealth() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiClient.refreshAccountHealth(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.accounts });
      queryClient.invalidateQueries({ queryKey: queryKeys.account(id) });
    },
  });
}

// Opportunities
export function useOpportunities(filters?: OpportunityFilters, page = 1, perPage = 20) {
  return useQuery({
    queryKey: queryKeys.opportunities(filters, page),
    queryFn: () => apiClient.getOpportunities(filters, page, perPage),
  });
}

export function useOpportunity(id: number) {
  return useQuery({
    queryKey: queryKeys.opportunity(id),
    queryFn: () => apiClient.getOpportunity(id),
    enabled: !!id,
  });
}

export function useUpdateOpportunityStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      apiClient.updateOpportunityStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['opportunities'] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}

export function useSkipOpportunity() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: number; reason?: string }) =>
      apiClient.skipOpportunity(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['opportunities'] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}

export function useBulkUpdateOpportunities() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ ids, action }: { ids: number[]; action: string }) =>
      apiClient.bulkUpdateOpportunities(ids, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['opportunities'] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}

// Content
export function useContents(filters?: ContentFilters, page = 1, perPage = 20) {
  return useQuery({
    queryKey: queryKeys.contents(filters, page),
    queryFn: () => apiClient.getContents(filters, page, perPage),
  });
}

export function useContent(id: number) {
  return useQuery({
    queryKey: queryKeys.content(id),
    queryFn: () => apiClient.getContent(id),
    enabled: !!id,
  });
}

export function useGenerateContent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (opportunityId: number) => apiClient.generateContent(opportunityId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      queryClient.invalidateQueries({ queryKey: ['opportunities'] });
    },
  });
}

export function useRegenerateContent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, feedback }: { id: number; feedback?: string }) =>
      apiClient.regenerateContent(id, feedback),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      queryClient.invalidateQueries({ queryKey: queryKeys.content(id) });
    },
  });
}

export function useApproveContent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiClient.approveContent(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}

export function useRejectContent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      apiClient.rejectContent(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
    },
  });
}

export function useUpdateContent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, contentText }: { id: number; contentText: string }) =>
      apiClient.updateContent(id, contentText),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      queryClient.invalidateQueries({ queryKey: queryKeys.content(id) });
    },
  });
}

export function usePublishContent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, accountId }: { id: number; accountId: number }) =>
      apiClient.publishContent(id, accountId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
      queryClient.invalidateQueries({ queryKey: queryKeys.accounts });
    },
  });
}

// Analytics
export function useAnalytics(projectId?: number, dateRange?: { start: string; end: string }) {
  return useQuery({
    queryKey: queryKeys.analytics(projectId, dateRange),
    queryFn: () => apiClient.getAnalytics(projectId, dateRange),
  });
}

// Subreddit Configs
export function useSubredditConfigs(projectId: number) {
  return useQuery({
    queryKey: queryKeys.subredditConfigs(projectId),
    queryFn: () => apiClient.getSubredditConfigs(projectId),
    enabled: !!projectId,
  });
}

export function useCreateSubredditConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, config }: { projectId: number; config: Partial<any> }) =>
      apiClient.createSubredditConfig(projectId, config),
    onSuccess: (_, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.subredditConfigs(projectId) });
    },
  });
}

export function useUpdateSubredditConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      configId,
      config,
    }: {
      projectId: number;
      configId: number;
      config: Partial<any>;
    }) => apiClient.updateSubredditConfig(projectId, configId, config),
    onSuccess: (_, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.subredditConfigs(projectId) });
    },
  });
}

export function useDeleteSubredditConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, configId }: { projectId: number; configId: number }) =>
      apiClient.deleteSubredditConfig(projectId, configId),
    onSuccess: (_, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.subredditConfigs(projectId) });
    },
  });
}

// Mining
export function useTriggerMining() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId?: number) => apiClient.triggerMining(projectId),
    onSuccess: () => {
      // Refetch opportunities after mining is triggered
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['opportunities'] });
      }, 5000);
    },
  });
}
