'use client';

import { useRouter } from 'next/navigation';
import {
  Inbox,
  FileEdit,
  Send,
  TrendingUp,
  Users,
  AlertTriangle,
  Zap,
  ArrowRight,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader, StatCard, UrgencyBadge } from '@/components/shared';
import { useDashboardStats, useOpportunities, useTriggerMining } from '@/hooks/use-queries';
import { useProjectStore } from '@/store/project-store';

export default function DashboardPage() {
  const router = useRouter();
  const { selectedProjectId } = useProjectStore();
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: recentOpportunities, isLoading: opportunitiesLoading } = useOpportunities(
    { status: ['new'], project_id: selectedProjectId || undefined },
    1,
    5
  );
  const triggerMining = useTriggerMining();

  const handleTriggerMining = () => {
    triggerMining.mutate(selectedProjectId || undefined);
  };

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Overview of your Reddit content platform"
        actions={
          <Button onClick={handleTriggerMining} disabled={triggerMining.isPending}>
            <Zap className="mr-2 h-4 w-4" />
            {triggerMining.isPending ? 'Mining...' : 'Trigger Mining'}
          </Button>
        }
      />

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
        {statsLoading ? (
          <>
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
          </>
        ) : (
          <>
            <StatCard
              title="Pending Opportunities"
              value={stats?.opportunities?.total || 0}
              icon={Inbox}
              description={`${stats?.opportunities?.new_today || 0} new today`}
            />
            <StatCard
              title="Pending Review"
              value={stats?.content?.pending_review || 0}
              icon={FileEdit}
              description="Content awaiting approval"
            />
            <StatCard
              title="Published Today"
              value={stats?.content?.published_today || 0}
              icon={Send}
              description={`${stats?.content?.total_published || 0} total published`}
            />
            <StatCard
              title="Total Upvotes"
              value={stats?.performance?.total_upvotes || 0}
              icon={TrendingUp}
              description={`${stats?.performance?.avg_engagement_rate?.toFixed(1) || 0}% avg engagement`}
            />
          </>
        )}
      </div>

      {/* Urgency Breakdown & Quick Actions */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 mb-8">
        {/* Urgency Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Opportunities by Urgency
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <div className="space-y-3">
                {[...Array(4)].map((_, i) => (
                  <Skeleton key={i} className="h-6 w-full" />
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                {(['critical', 'high', 'medium', 'low'] as const).map((level) => (
                  <div key={level} className="flex items-center justify-between">
                    <UrgencyBadge level={level} />
                    <span className="font-semibold">
                      {stats?.opportunities?.by_urgency?.[level] || 0}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Account Health */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Account Health
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <div className="space-y-3">
                {[...Array(3)].map((_, i) => (
                  <Skeleton key={i} className="h-6 w-full" />
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Total Accounts</span>
                  <span className="font-semibold">{stats?.accounts?.total || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-green-600">Healthy</span>
                  <span className="font-semibold text-green-600">
                    {stats?.accounts?.healthy || 0}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-yellow-600">In Cooldown</span>
                  <span className="font-semibold text-yellow-600">
                    {stats?.accounts?.in_cooldown || 0}
                  </span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button
              variant="outline"
              className="w-full justify-between"
              onClick={() => router.push('/queue')}
            >
              Review Opportunity Queue
              <ArrowRight className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              className="w-full justify-between"
              onClick={() => router.push('/content')}
            >
              Review Pending Content
              <ArrowRight className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              className="w-full justify-between"
              onClick={() => router.push('/projects')}
            >
              Manage Projects
              <ArrowRight className="h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Recent Opportunities */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Recent Opportunities</CardTitle>
          <Button variant="ghost" size="sm" onClick={() => router.push('/queue')}>
            View All
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent>
          {opportunitiesLoading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-12 w-12 rounded" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-3 w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          ) : recentOpportunities?.items?.length ? (
            <div className="space-y-4">
              {recentOpportunities.items.map((opp) => (
                <div
                  key={opp.id}
                  className="flex items-center gap-4 p-3 rounded-lg border cursor-pointer hover:bg-muted/50 transition-colors"
                  onClick={() => router.push(`/queue?id=${opp.id}`)}
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{opp.post_title}</p>
                    <p className="text-sm text-muted-foreground">
                      r/{opp.subreddit} • {opp.post_score} points • {opp.post_num_comments} comments
                    </p>
                  </div>
                  <UrgencyBadge level={opp.urgency_level} />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-8">
              No new opportunities. Try triggering a mining run!
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
