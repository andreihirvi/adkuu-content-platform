'use client';

import { useState } from 'react';
import {
  Plus,
  RefreshCw,
  MoreVertical,
  Trash2,
  Activity,
  Clock,
  Shield,
  AlertTriangle,
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { PageHeader, EmptyState } from '@/components/shared';
import {
  useRedditAccounts,
  useInitiateRedditOAuth,
  useDisconnectAccount,
  useRefreshAccountHealth,
} from '@/hooks/use-queries';
import type { RedditAccount } from '@/types';
import { cn } from '@/lib/utils';

const healthConfig: Record<RedditAccount['health_status'], { label: string; color: string; icon: typeof Shield }> = {
  healthy: { label: 'Healthy', color: 'text-green-600', icon: Shield },
  warning: { label: 'Warning', color: 'text-yellow-600', icon: AlertTriangle },
  suspended: { label: 'Suspended', color: 'text-red-600', icon: AlertTriangle },
  unknown: { label: 'Unknown', color: 'text-muted-foreground', icon: Activity },
};

export default function AccountsPage() {
  const { data: accounts, isLoading, refetch } = useRedditAccounts();
  const initiateOAuth = useInitiateRedditOAuth();
  const disconnectAccount = useDisconnectAccount();
  const refreshHealth = useRefreshAccountHealth();

  const [disconnectingAccount, setDisconnectingAccount] = useState<RedditAccount | null>(null);

  const handleConnectAccount = async () => {
    try {
      const result = await initiateOAuth.mutateAsync();
      // Redirect to Reddit OAuth
      window.location.href = result.auth_url;
    } catch (error) {
      console.error('Failed to initiate OAuth:', error);
    }
  };

  const handleDisconnect = () => {
    if (!disconnectingAccount) return;
    disconnectAccount.mutate(disconnectingAccount.id, {
      onSuccess: () => {
        setDisconnectingAccount(null);
      },
    });
  };

  const handleRefreshHealth = (id: number) => {
    refreshHealth.mutate(id);
  };

  return (
    <div>
      <PageHeader
        title="Reddit Accounts"
        description="Manage connected Reddit accounts for publishing"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="icon" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button onClick={handleConnectAccount} disabled={initiateOAuth.isPending}>
              <Plus className="mr-2 h-4 w-4" />
              Connect Account
            </Button>
          </div>
        }
      />

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(3)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : !accounts?.length ? (
        <EmptyState
          title="No accounts connected"
          description="Connect a Reddit account to start publishing content"
          action={{
            label: 'Connect Account',
            onClick: handleConnectAccount,
          }}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {accounts.map((account) => {
            const health = healthConfig[account.health_status];
            const HealthIcon = health.icon;
            const isInCooldown = account.cooldown_until && new Date(account.cooldown_until) > new Date();

            return (
              <Card key={account.id}>
                <CardHeader className="flex flex-row items-start justify-between space-y-0">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      u/{account.username}
                      <Badge variant={account.is_active ? 'default' : 'secondary'}>
                        {account.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </CardTitle>
                    <CardDescription className="flex items-center gap-1 mt-1">
                      <HealthIcon className={cn('h-4 w-4', health.color)} />
                      <span className={health.color}>{health.label}</span>
                    </CardDescription>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => handleRefreshHealth(account.id)}>
                        <RefreshCw className="mr-2 h-4 w-4" />
                        Refresh Health
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className="text-destructive"
                        onClick={() => setDisconnectingAccount(account)}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Disconnect
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-muted-foreground">Karma</p>
                        <p className="text-lg font-semibold">
                          {account.karma_score?.toLocaleString() || 'N/A'}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Account Age</p>
                        <p className="text-lg font-semibold">
                          {account.account_age_days
                            ? `${Math.floor(account.account_age_days / 365)}y ${Math.floor((account.account_age_days % 365) / 30)}m`
                            : 'N/A'}
                        </p>
                      </div>
                    </div>

                    <div className="space-y-2 pt-2 border-t">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">Comments Today</span>
                        <span className="font-medium">{account.daily_comment_count}</span>
                      </div>
                      {account.last_used_at && (
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground">Last Used</span>
                          <span className="font-medium">
                            {formatDistanceToNow(new Date(account.last_used_at), { addSuffix: true })}
                          </span>
                        </div>
                      )}
                    </div>

                    {isInCooldown && (
                      <div className="flex items-center gap-2 p-2 rounded-lg bg-yellow-500/10 text-yellow-700">
                        <Clock className="h-4 w-4" />
                        <span className="text-sm">
                          Cooldown until{' '}
                          {format(new Date(account.cooldown_until!), 'MMM d, h:mm a')}
                        </span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Disconnect Confirmation Dialog */}
      <Dialog open={!!disconnectingAccount} onOpenChange={() => setDisconnectingAccount(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Disconnect Account</DialogTitle>
          </DialogHeader>
          <p className="text-muted-foreground">
            Are you sure you want to disconnect u/{disconnectingAccount?.username}? You'll need to
            reconnect it to use it for publishing again.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDisconnectingAccount(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDisconnect}
              disabled={disconnectAccount.isPending}
            >
              Disconnect
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
