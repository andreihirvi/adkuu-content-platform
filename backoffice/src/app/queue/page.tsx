'use client';

import { useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Filter,
  RefreshCw,
  ExternalLink,
  Clock,
  MessageSquare,
  TrendingUp,
  SkipForward,
  Sparkles,
  CheckCircle,
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import {
  PageHeader,
  SplitPane,
  UrgencyBadge,
  ScoreBar,
  EmptyState,
} from '@/components/shared';
import {
  useOpportunities,
  useOpportunity,
  useGenerateContent,
  useSkipOpportunity,
  useBulkUpdateOpportunities,
} from '@/hooks/use-queries';
import { useOpportunityStore } from '@/store/opportunity-store';
import { useProjectStore } from '@/store/project-store';
import { cn } from '@/lib/utils';
import type { Opportunity } from '@/types';

export default function QueuePage() {
  const searchParams = useSearchParams();
  const { selectedProjectId } = useProjectStore();
  const {
    filters,
    quickFilter,
    setQuickFilter,
    selectedIds,
    toggleSelected,
    selectAll,
    clearSelection,
    selectedOpportunityId,
    setSelectedOpportunity,
  } = useOpportunityStore();

  // Apply project filter
  const appliedFilters = {
    ...filters,
    project_id: selectedProjectId || undefined,
  };

  const { data: opportunities, isLoading, refetch } = useOpportunities(appliedFilters);
  const { data: selectedOpp, isLoading: oppLoading } = useOpportunity(selectedOpportunityId || 0);

  const generateContent = useGenerateContent();
  const skipOpportunity = useSkipOpportunity();
  const bulkUpdate = useBulkUpdateOpportunities();

  // Set selected opportunity from URL param
  useEffect(() => {
    const id = searchParams.get('id');
    if (id) {
      setSelectedOpportunity(parseInt(id));
    }
  }, [searchParams, setSelectedOpportunity]);

  // Auto-select first opportunity
  useEffect(() => {
    if (!selectedOpportunityId && opportunities?.items?.length) {
      setSelectedOpportunity(opportunities.items[0].id);
    }
  }, [opportunities, selectedOpportunityId, setSelectedOpportunity]);

  const handleGenerate = () => {
    if (selectedOpportunityId) {
      generateContent.mutate(selectedOpportunityId);
    }
  };

  const handleSkip = () => {
    if (selectedOpportunityId) {
      skipOpportunity.mutate({ id: selectedOpportunityId });
    }
  };

  const handleBulkAction = (action: string) => {
    if (selectedIds.length > 0) {
      bulkUpdate.mutate({ ids: selectedIds, action });
      clearSelection();
    }
  };

  return (
    <div>
      <PageHeader
        title="Opportunity Queue"
        description="Review and act on discovered Reddit opportunities"
        actions={
          <div className="flex items-center gap-2">
            {selectedIds.length > 0 && (
              <>
                <span className="text-sm text-muted-foreground">
                  {selectedIds.length} selected
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleBulkAction('skip')}
                >
                  Skip Selected
                </Button>
                <Button variant="outline" size="sm" onClick={clearSelection}>
                  Clear
                </Button>
              </>
            )}
            <Button variant="outline" size="icon" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        }
      />

      {/* Quick Filters */}
      <div className="flex items-center gap-4 mb-4">
        <Tabs
          value={quickFilter}
          onValueChange={(v) => setQuickFilter(v as typeof quickFilter)}
        >
          <TabsList>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="urgent">Urgent</TabsTrigger>
            <TabsTrigger value="new">New</TabsTrigger>
            <TabsTrigger value="queued">In Progress</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <SplitPane
        left={
          <OpportunityList
            opportunities={opportunities?.items || []}
            isLoading={isLoading}
            selectedId={selectedOpportunityId}
            selectedIds={selectedIds}
            onSelect={setSelectedOpportunity}
            onToggleSelect={toggleSelected}
            onSelectAll={() =>
              selectAll(opportunities?.items?.map((o) => o.id) || [])
            }
          />
        }
        right={
          <OpportunityDetail
            opportunity={selectedOpp}
            isLoading={oppLoading}
            onGenerate={handleGenerate}
            onSkip={handleSkip}
            isGenerating={generateContent.isPending}
            isSkipping={skipOpportunity.isPending}
          />
        }
      />
    </div>
  );
}

interface OpportunityListProps {
  opportunities: Opportunity[];
  isLoading: boolean;
  selectedId: number | null;
  selectedIds: number[];
  onSelect: (id: number) => void;
  onToggleSelect: (id: number) => void;
  onSelectAll: () => void;
}

function OpportunityList({
  opportunities,
  isLoading,
  selectedId,
  selectedIds,
  onSelect,
  onToggleSelect,
  onSelectAll,
}: OpportunityListProps) {
  if (isLoading) {
    return (
      <div className="p-4 space-y-3">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="flex gap-3">
            <Skeleton className="h-4 w-4" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-3 w-2/3" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!opportunities.length) {
    return (
      <EmptyState
        title="No opportunities"
        description="No opportunities match your current filters. Try adjusting or triggering a new mining run."
      />
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* List Header */}
      <div className="flex items-center gap-2 p-3 border-b">
        <Checkbox
          checked={selectedIds.length === opportunities.length && opportunities.length > 0}
          onCheckedChange={() => {
            if (selectedIds.length === opportunities.length) {
              onToggleSelect(-1); // Clear all
            } else {
              onSelectAll();
            }
          }}
        />
        <span className="text-sm text-muted-foreground">
          {opportunities.length} opportunities
        </span>
      </div>

      {/* List */}
      <ScrollArea className="flex-1">
        <div className="divide-y">
          {opportunities.map((opp) => (
            <div
              key={opp.id}
              className={cn(
                'flex items-start gap-3 p-3 cursor-pointer transition-colors hover:bg-muted/50',
                selectedId === opp.id && 'bg-muted'
              )}
              onClick={() => onSelect(opp.id)}
            >
              <Checkbox
                checked={selectedIds.includes(opp.id)}
                onClick={(e) => e.stopPropagation()}
                onCheckedChange={() => onToggleSelect(opp.id)}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <UrgencyBadge level={opp.urgency_level} />
                  <span className="text-xs text-muted-foreground">
                    r/{opp.subreddit}
                  </span>
                </div>
                <p className="font-medium text-sm truncate">{opp.post_title}</p>
                <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <TrendingUp className="h-3 w-3" />
                    {opp.post_score}
                  </span>
                  <span className="flex items-center gap-1">
                    <MessageSquare className="h-3 w-3" />
                    {opp.post_num_comments}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {formatDistanceToNow(new Date(opp.discovered_at), { addSuffix: true })}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}

interface OpportunityDetailProps {
  opportunity?: Opportunity;
  isLoading: boolean;
  onGenerate: () => void;
  onSkip: () => void;
  isGenerating: boolean;
  isSkipping: boolean;
}

function OpportunityDetail({
  opportunity,
  isLoading,
  onGenerate,
  onSkip,
  isGenerating,
  isSkipping,
}: OpportunityDetailProps) {
  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (!opportunity) {
    return (
      <EmptyState
        title="Select an opportunity"
        description="Click on an opportunity from the list to view details"
      />
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <UrgencyBadge level={opportunity.urgency_level} />
            <Badge variant="outline">{opportunity.status}</Badge>
            <Badge variant="secondary">r/{opportunity.subreddit}</Badge>
          </div>
          <h2 className="text-xl font-semibold">{opportunity.post_title}</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Posted by u/{opportunity.post_author} •{' '}
            {formatDistanceToNow(new Date(opportunity.post_created_utc), { addSuffix: true })}
          </p>
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-4 rounded-lg bg-muted">
            <TrendingUp className="h-5 w-5 mx-auto mb-1 text-muted-foreground" />
            <p className="text-2xl font-bold">{opportunity.post_score}</p>
            <p className="text-xs text-muted-foreground">Score</p>
          </div>
          <div className="text-center p-4 rounded-lg bg-muted">
            <MessageSquare className="h-5 w-5 mx-auto mb-1 text-muted-foreground" />
            <p className="text-2xl font-bold">{opportunity.post_num_comments}</p>
            <p className="text-xs text-muted-foreground">Comments</p>
          </div>
          <div className="text-center p-4 rounded-lg bg-muted">
            <CheckCircle className="h-5 w-5 mx-auto mb-1 text-muted-foreground" />
            <p className="text-2xl font-bold">{opportunity.relevance_score}</p>
            <p className="text-xs text-muted-foreground">Relevance</p>
          </div>
        </div>

        {/* Relevance Score Bar */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Relevance Score</span>
            <span className="text-sm text-muted-foreground">{opportunity.relevance_score}/100</span>
          </div>
          <ScoreBar value={opportunity.relevance_score} size="lg" showValue={false} />
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <Button className="flex-1" onClick={onGenerate} disabled={isGenerating}>
            {isGenerating ? (
              <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="mr-2 h-4 w-4" />
            )}
            {isGenerating ? 'Generating...' : 'Generate Content'}
          </Button>
          <Button variant="outline" onClick={onSkip} disabled={isSkipping}>
            <SkipForward className="mr-2 h-4 w-4" />
            Skip
          </Button>
          <Button variant="outline" size="icon" asChild>
            <a href={opportunity.post_url} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-4 w-4" />
            </a>
          </Button>
        </div>

        {/* Timeline */}
        <div className="space-y-2">
          <h3 className="font-medium">Timeline</h3>
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span>
                Discovered {format(new Date(opportunity.discovered_at), 'PPp')}
              </span>
            </div>
            {opportunity.expires_at && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Clock className="h-4 w-4" />
                <span>
                  Expires {format(new Date(opportunity.expires_at), 'PPp')}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Generated Content */}
        {opportunity.generated_contents && opportunity.generated_contents.length > 0 && (
          <div className="space-y-2">
            <h3 className="font-medium">Generated Content</h3>
            <div className="space-y-2">
              {opportunity.generated_contents.map((content) => (
                <div key={content.id} className="p-3 rounded-lg bg-muted">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant={content.status === 'published' ? 'default' : 'secondary'}>
                      {content.status}
                    </Badge>
                    {content.quality_score && (
                      <span className="text-xs text-muted-foreground">
                        Quality: {content.quality_score}/100
                      </span>
                    )}
                  </div>
                  <p className="text-sm whitespace-pre-wrap">{content.content_text}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </ScrollArea>
  );
}
