'use client';

import { useState } from 'react';
import {
  RefreshCw,
  Check,
  X,
  RotateCcw,
  Send,
  Edit2,
  Save,
  ExternalLink,
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import {
  PageHeader,
  SplitPane,
  ScoreBar,
  EmptyState,
} from '@/components/shared';
import {
  useContents,
  useContent,
  useApproveContent,
  useRejectContent,
  useRegenerateContent,
  useUpdateContent,
  usePublishContent,
  useRedditAccounts,
} from '@/hooks/use-queries';
import { useContentStore } from '@/store/content-store';
import { useProjectStore } from '@/store/project-store';
import { cn } from '@/lib/utils';
import type { GeneratedContent, ContentStatus } from '@/types';

const statusConfig: Record<ContentStatus, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  draft: { label: 'Draft', variant: 'secondary' },
  pending_review: { label: 'Pending Review', variant: 'outline' },
  approved: { label: 'Approved', variant: 'default' },
  rejected: { label: 'Rejected', variant: 'destructive' },
  published: { label: 'Published', variant: 'default' },
  failed: { label: 'Failed', variant: 'destructive' },
};

export default function ContentPage() {
  const { selectedProjectId } = useProjectStore();
  const {
    filters,
    quickFilter,
    setQuickFilter,
    selectedContentId,
    setSelectedContent,
    isEditing,
    setIsEditing,
    editedText,
    setEditedText,
  } = useContentStore();

  const appliedFilters = {
    ...filters,
    project_id: selectedProjectId || undefined,
  };

  const { data: contents, isLoading, refetch } = useContents(appliedFilters);
  const { data: selectedContent, isLoading: contentLoading } = useContent(selectedContentId || 0);
  const { data: accounts } = useRedditAccounts();

  const approveContent = useApproveContent();
  const rejectContent = useRejectContent();
  const regenerateContent = useRegenerateContent();
  const updateContent = useUpdateContent();
  const publishContent = usePublishContent();

  const [rejectReason, setRejectReason] = useState('');
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [showPublishDialog, setShowPublishDialog] = useState(false);
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);

  const handleApprove = () => {
    if (selectedContentId) {
      approveContent.mutate(selectedContentId);
    }
  };

  const handleReject = () => {
    if (selectedContentId && rejectReason) {
      rejectContent.mutate({ id: selectedContentId, reason: rejectReason });
      setShowRejectDialog(false);
      setRejectReason('');
    }
  };

  const handleRegenerate = () => {
    if (selectedContentId) {
      regenerateContent.mutate({ id: selectedContentId });
    }
  };

  const handleSaveEdit = () => {
    if (selectedContentId && editedText) {
      updateContent.mutate({ id: selectedContentId, contentText: editedText });
      setIsEditing(false);
    }
  };

  const handlePublish = () => {
    if (selectedContentId && selectedAccountId) {
      publishContent.mutate({ id: selectedContentId, accountId: selectedAccountId });
      setShowPublishDialog(false);
      setSelectedAccountId(null);
    }
  };

  const startEditing = () => {
    if (selectedContent) {
      setEditedText(selectedContent.content_text);
      setIsEditing(true);
    }
  };

  // Auto-select first content
  if (!selectedContentId && contents?.items?.length) {
    setSelectedContent(contents.items[0].id);
  }

  return (
    <div>
      <PageHeader
        title="Content Review"
        description="Review, edit, and approve generated content"
        actions={
          <Button variant="outline" size="icon" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" />
          </Button>
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
            <TabsTrigger value="pending">Pending</TabsTrigger>
            <TabsTrigger value="approved">Approved</TabsTrigger>
            <TabsTrigger value="published">Published</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <SplitPane
        left={
          <ContentList
            contents={contents?.items || []}
            isLoading={isLoading}
            selectedId={selectedContentId}
            onSelect={setSelectedContent}
          />
        }
        right={
          <ContentDetail
            content={selectedContent}
            isLoading={contentLoading}
            isEditing={isEditing}
            editedText={editedText}
            onEditedTextChange={setEditedText}
            onApprove={handleApprove}
            onReject={() => setShowRejectDialog(true)}
            onRegenerate={handleRegenerate}
            onStartEdit={startEditing}
            onSaveEdit={handleSaveEdit}
            onCancelEdit={() => setIsEditing(false)}
            onPublish={() => setShowPublishDialog(true)}
            isApproving={approveContent.isPending}
            isRegenerating={regenerateContent.isPending}
            isSaving={updateContent.isPending}
          />
        }
      />

      {/* Reject Dialog */}
      <Dialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject Content</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Reason for rejection</Label>
              <Textarea
                placeholder="Explain why this content is being rejected..."
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRejectDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleReject}
              disabled={!rejectReason || rejectContent.isPending}
            >
              Reject
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Publish Dialog */}
      <Dialog open={showPublishDialog} onOpenChange={setShowPublishDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Publish Content</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Select Reddit Account</Label>
              <Select
                value={selectedAccountId?.toString() || ''}
                onValueChange={(v) => setSelectedAccountId(parseInt(v))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Choose an account" />
                </SelectTrigger>
                <SelectContent>
                  {accounts
                    ?.filter((a) => a.is_active && a.health_status === 'healthy')
                    .map((account) => (
                      <SelectItem key={account.id} value={account.id.toString()}>
                        u/{account.username} ({account.karma_score} karma)
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPublishDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handlePublish}
              disabled={!selectedAccountId || publishContent.isPending}
            >
              <Send className="mr-2 h-4 w-4" />
              Publish
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

interface ContentListProps {
  contents: GeneratedContent[];
  isLoading: boolean;
  selectedId: number | null;
  onSelect: (id: number) => void;
}

function ContentList({ contents, isLoading, selectedId, onSelect }: ContentListProps) {
  if (isLoading) {
    return (
      <div className="p-4 space-y-3">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-3 w-2/3" />
          </div>
        ))}
      </div>
    );
  }

  if (!contents.length) {
    return (
      <EmptyState
        title="No content"
        description="No content matches your current filters."
      />
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="divide-y">
        {contents.map((content) => {
          const config = statusConfig[content.status];
          return (
            <div
              key={content.id}
              className={cn(
                'p-3 cursor-pointer transition-colors hover:bg-muted/50',
                selectedId === content.id && 'bg-muted'
              )}
              onClick={() => onSelect(content.id)}
            >
              <div className="flex items-center gap-2 mb-2">
                <Badge variant={config.variant}>{config.label}</Badge>
                {content.quality_score && (
                  <span className="text-xs text-muted-foreground">
                    Q: {content.quality_score}
                  </span>
                )}
              </div>
              <p className="text-sm line-clamp-2">{content.content_text}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {formatDistanceToNow(new Date(content.created_at), { addSuffix: true })}
              </p>
            </div>
          );
        })}
      </div>
    </ScrollArea>
  );
}

interface ContentDetailProps {
  content?: GeneratedContent;
  isLoading: boolean;
  isEditing: boolean;
  editedText: string;
  onEditedTextChange: (text: string) => void;
  onApprove: () => void;
  onReject: () => void;
  onRegenerate: () => void;
  onStartEdit: () => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onPublish: () => void;
  isApproving: boolean;
  isRegenerating: boolean;
  isSaving: boolean;
}

function ContentDetail({
  content,
  isLoading,
  isEditing,
  editedText,
  onEditedTextChange,
  onApprove,
  onReject,
  onRegenerate,
  onStartEdit,
  onSaveEdit,
  onCancelEdit,
  onPublish,
  isApproving,
  isRegenerating,
  isSaving,
}: ContentDetailProps) {
  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (!content) {
    return (
      <EmptyState
        title="Select content"
        description="Click on content from the list to view details"
      />
    );
  }

  const config = statusConfig[content.status];
  const canApprove = content.status === 'pending_review' || content.status === 'draft';
  const canPublish = content.status === 'approved';

  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant={config.variant}>{config.label}</Badge>
            <Badge variant="secondary">{content.content_type}</Badge>
          </div>
          <span className="text-sm text-muted-foreground">
            Generated {format(new Date(content.created_at), 'PPp')}
          </span>
        </div>

        {/* Quality Scores */}
        {(content.quality_score || content.authenticity_score || content.relevance_score) && (
          <div className="grid grid-cols-3 gap-4">
            {content.quality_score && (
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>Quality</span>
                  <span>{content.quality_score}</span>
                </div>
                <ScoreBar value={content.quality_score} showValue={false} />
              </div>
            )}
            {content.authenticity_score && (
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>Authenticity</span>
                  <span>{content.authenticity_score}</span>
                </div>
                <ScoreBar value={content.authenticity_score} showValue={false} />
              </div>
            )}
            {content.relevance_score && (
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>Relevance</span>
                  <span>{content.relevance_score}</span>
                </div>
                <ScoreBar value={content.relevance_score} showValue={false} />
              </div>
            )}
          </div>
        )}

        {/* Content */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">Content</h3>
            {!isEditing && canApprove && (
              <Button variant="ghost" size="sm" onClick={onStartEdit}>
                <Edit2 className="mr-2 h-4 w-4" />
                Edit
              </Button>
            )}
          </div>
          {isEditing ? (
            <div className="space-y-2">
              <Textarea
                value={editedText}
                onChange={(e) => onEditedTextChange(e.target.value)}
                rows={10}
                className="font-mono text-sm"
              />
              <div className="flex gap-2">
                <Button size="sm" onClick={onSaveEdit} disabled={isSaving}>
                  <Save className="mr-2 h-4 w-4" />
                  Save
                </Button>
                <Button variant="outline" size="sm" onClick={onCancelEdit}>
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div className="p-4 rounded-lg bg-muted whitespace-pre-wrap text-sm">
              {content.content_text}
            </div>
          )}
        </div>

        {/* Rejection Reason */}
        {content.status === 'rejected' && content.rejection_reason && (
          <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/20">
            <h4 className="font-medium text-destructive mb-1">Rejection Reason</h4>
            <p className="text-sm">{content.rejection_reason}</p>
          </div>
        )}

        {/* Related Opportunity */}
        {content.opportunity && (
          <div className="space-y-2">
            <h3 className="font-medium">Related Opportunity</h3>
            <div className="p-4 rounded-lg border">
              <p className="font-medium">{content.opportunity.post_title}</p>
              <p className="text-sm text-muted-foreground">
                r/{content.opportunity.subreddit}
              </p>
              <Button variant="link" size="sm" className="px-0 mt-2" asChild>
                <a
                  href={content.opportunity.post_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  View on Reddit
                  <ExternalLink className="ml-1 h-3 w-3" />
                </a>
              </Button>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-4 border-t">
          {canApprove && (
            <>
              <Button onClick={onApprove} disabled={isApproving}>
                <Check className="mr-2 h-4 w-4" />
                Approve
              </Button>
              <Button variant="outline" onClick={onReject}>
                <X className="mr-2 h-4 w-4" />
                Reject
              </Button>
            </>
          )}
          {canPublish && (
            <Button onClick={onPublish}>
              <Send className="mr-2 h-4 w-4" />
              Publish
            </Button>
          )}
          {(canApprove || content.status === 'rejected') && (
            <Button variant="outline" onClick={onRegenerate} disabled={isRegenerating}>
              <RotateCcw className="mr-2 h-4 w-4" />
              Regenerate
            </Button>
          )}
        </div>
      </div>
    </ScrollArea>
  );
}
