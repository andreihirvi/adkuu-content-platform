'use client';

import { useState } from 'react';
import {
  ExternalLink,
  RefreshCw,
  TrendingUp,
  MessageSquare,
  Clock,
  Star,
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { PageHeader, EmptyState } from '@/components/shared';
import { useContents } from '@/hooks/use-queries';
import { useProjectStore } from '@/store/project-store';
import { cn } from '@/lib/utils';

export default function PublishedPage() {
  const { selectedProjectId } = useProjectStore();
  const [page, setPage] = useState(1);

  const { data, isLoading, refetch } = useContents(
    {
      status: ['published'],
      project_id: selectedProjectId || undefined,
    },
    page,
    20
  );

  return (
    <div>
      <PageHeader
        title="Published Content"
        description="Track your published Reddit content and performance"
        actions={
          <Button variant="outline" size="icon" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        }
      />

      {isLoading ? (
        <Card>
          <CardContent className="p-0">
            <div className="space-y-4 p-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex gap-4">
                  <Skeleton className="h-16 w-16" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-3 w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : !data?.items?.length ? (
        <EmptyState
          title="No published content"
          description="Content will appear here after it's been published to Reddit"
        />
      ) : (
        <>
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[40%]">Content</TableHead>
                    <TableHead>Subreddit</TableHead>
                    <TableHead>Performance</TableHead>
                    <TableHead>Published</TableHead>
                    <TableHead className="w-[100px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((content) => (
                    <TableRow key={content.id}>
                      <TableCell>
                        <p className="font-medium line-clamp-2 max-w-md">
                          {content.content_text}
                        </p>
                        {content.opportunity && (
                          <p className="text-sm text-muted-foreground mt-1 truncate max-w-md">
                            Re: {content.opportunity.post_title}
                          </p>
                        )}
                      </TableCell>
                      <TableCell>
                        {content.opportunity && (
                          <Badge variant="outline">
                            r/{content.opportunity.subreddit}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {content.performance ? (
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <TrendingUp
                                className={cn(
                                  'h-4 w-4',
                                  content.performance.score > 0
                                    ? 'text-green-600'
                                    : content.performance.score < 0
                                    ? 'text-red-600'
                                    : 'text-muted-foreground'
                                )}
                              />
                              <span className="font-medium">
                                {content.performance.score > 0 ? '+' : ''}
                                {content.performance.score}
                              </span>
                            </div>
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              <MessageSquare className="h-3 w-3" />
                              <span>{content.performance.num_replies} replies</span>
                              {content.performance.is_top_comment && (
                                <Badge variant="secondary" className="ml-2">
                                  <Star className="h-3 w-3 mr-1" />
                                  Top
                                </Badge>
                              )}
                            </div>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">Pending...</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1 text-sm text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          {content.published_at
                            ? formatDistanceToNow(new Date(content.published_at), {
                                addSuffix: true,
                              })
                            : 'N/A'}
                        </div>
                      </TableCell>
                      <TableCell>
                        {content.reddit_comment_id && content.opportunity && (
                          <Button variant="ghost" size="icon" asChild>
                            <a
                              href={`${content.opportunity.post_url}${content.reddit_comment_id}`}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              <ExternalLink className="h-4 w-4" />
                            </a>
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Pagination */}
          {data.pages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {data.pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(page + 1)}
                disabled={page === data.pages}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
