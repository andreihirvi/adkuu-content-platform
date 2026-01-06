'use client';

import { useState } from 'react';
import {
  TrendingUp,
  ArrowUp,
  MessageSquare,
  Star,
  Calendar,
} from 'lucide-react';
import { format, subDays } from 'date-fns';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { PageHeader, StatCard } from '@/components/shared';
import { useAnalytics, useProjects } from '@/hooks/use-queries';
import { useProjectStore } from '@/store/project-store';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

type DateRange = '7d' | '14d' | '30d' | '90d';

export default function AnalyticsPage() {
  const { selectedProjectId } = useProjectStore();
  const { data: projects } = useProjects();
  const [dateRange, setDateRange] = useState<DateRange>('30d');

  const days = {
    '7d': 7,
    '14d': 14,
    '30d': 30,
    '90d': 90,
  }[dateRange];

  const dateRangeParams = {
    start: format(subDays(new Date(), days), 'yyyy-MM-dd'),
    end: format(new Date(), 'yyyy-MM-dd'),
  };

  const { data: analytics, isLoading } = useAnalytics(
    selectedProjectId || undefined,
    dateRangeParams
  );

  return (
    <div>
      <PageHeader
        title="Analytics"
        description="Track performance of your published content"
        actions={
          <div className="flex items-center gap-2">
            <Select value={dateRange} onValueChange={(v) => setDateRange(v as DateRange)}>
              <SelectTrigger className="w-[140px]">
                <Calendar className="mr-2 h-4 w-4" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7d">Last 7 days</SelectItem>
                <SelectItem value="14d">Last 14 days</SelectItem>
                <SelectItem value="30d">Last 30 days</SelectItem>
                <SelectItem value="90d">Last 90 days</SelectItem>
              </SelectContent>
            </Select>
          </div>
        }
      />

      {isLoading ? (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <Card key={i}>
                <CardHeader className="pb-2">
                  <Skeleton className="h-4 w-24" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-16" />
                </CardContent>
              </Card>
            ))}
          </div>
          <Card>
            <CardHeader>
              <Skeleton className="h-6 w-32" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-64 w-full" />
            </CardContent>
          </Card>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Summary Stats */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            <StatCard
              title="Total Published"
              value={analytics?.summary?.total_published || 0}
              icon={MessageSquare}
            />
            <StatCard
              title="Total Upvotes"
              value={analytics?.summary?.total_upvotes?.toLocaleString() || 0}
              icon={ArrowUp}
            />
            <StatCard
              title="Average Score"
              value={analytics?.summary?.avg_score?.toFixed(1) || 0}
              icon={TrendingUp}
            />
            <StatCard
              title="Top Comments"
              value={analytics?.summary?.top_comments || 0}
              icon={Star}
              description="In top 10 of threads"
            />
            <StatCard
              title="Total Engagement"
              value={analytics?.summary?.total_engagement?.toLocaleString() || 0}
              description="Upvotes + replies"
            />
          </div>

          {/* Charts Row */}
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Daily Performance Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Daily Performance</CardTitle>
                <CardDescription>Published content and engagement over time</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  {analytics?.daily_stats?.length ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={analytics.daily_stats}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis
                          dataKey="date"
                          tickFormatter={(value) => format(new Date(value), 'MMM d')}
                          className="text-xs"
                        />
                        <YAxis className="text-xs" />
                        <Tooltip
                          labelFormatter={(value) => format(new Date(value), 'MMM d, yyyy')}
                          contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            border: '1px solid hsl(var(--border))',
                            borderRadius: '8px',
                          }}
                        />
                        <Line
                          type="monotone"
                          dataKey="upvotes"
                          stroke="#0088FE"
                          strokeWidth={2}
                          dot={false}
                          name="Upvotes"
                        />
                        <Line
                          type="monotone"
                          dataKey="published"
                          stroke="#00C49F"
                          strokeWidth={2}
                          dot={false}
                          name="Published"
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex items-center justify-center h-full text-muted-foreground">
                      No data for this period
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Subreddit Performance */}
            <Card>
              <CardHeader>
                <CardTitle>Subreddit Performance</CardTitle>
                <CardDescription>Engagement by subreddit</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  {analytics?.subreddit_performance?.length ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={analytics.subreddit_performance.slice(0, 8)} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis type="number" className="text-xs" />
                        <YAxis
                          dataKey="subreddit"
                          type="category"
                          width={100}
                          tickFormatter={(value) => `r/${value}`}
                          className="text-xs"
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            border: '1px solid hsl(var(--border))',
                            borderRadius: '8px',
                          }}
                        />
                        <Bar dataKey="total_upvotes" fill="#0088FE" name="Total Upvotes" />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex items-center justify-center h-full text-muted-foreground">
                      No subreddit data
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Top Performing Content */}
          <Card>
            <CardHeader>
              <CardTitle>Top Performing Content</CardTitle>
              <CardDescription>Your best performing published content</CardDescription>
            </CardHeader>
            <CardContent>
              {analytics?.top_content?.length ? (
                <div className="space-y-4">
                  {analytics.top_content.map((content, index) => (
                    <div
                      key={content.id}
                      className="flex items-start gap-4 p-4 rounded-lg border"
                    >
                      <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary font-bold">
                        {index + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium line-clamp-2">{content.content_text}</p>
                        {content.opportunity && (
                          <p className="text-sm text-muted-foreground mt-1">
                            r/{content.opportunity.subreddit} •{' '}
                            {content.opportunity.post_title}
                          </p>
                        )}
                      </div>
                      <div className="text-right">
                        {content.performance ? (
                          <>
                            <p className="font-bold text-lg">
                              {content.performance.score > 0 ? '+' : ''}
                              {content.performance.score}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {content.performance.num_replies} replies
                            </p>
                          </>
                        ) : (
                          <p className="text-muted-foreground">No data</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  No published content yet
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
