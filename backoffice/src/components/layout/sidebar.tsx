'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Inbox,
  FileEdit,
  Send,
  FolderKanban,
  Users,
  UserCog,
  BarChart3,
  Settings,
  ChevronLeft,
  ChevronRight,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { useUIStore } from '@/store/ui-store';
import { useAuthStore } from '@/store/auth-store';
import { useDashboardStats } from '@/hooks/use-queries';

interface NavItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  badge?: 'urgent' | 'pending';
  adminOnly?: boolean;
}

interface NavGroup {
  id: string;
  label?: string;
  items: NavItem[];
}

const navigationGroups: NavGroup[] = [
  {
    id: 'main',
    items: [
      { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, href: '/' },
    ],
  },
  {
    id: 'workflow',
    label: 'Workflow',
    items: [
      { id: 'queue', label: 'Opportunity Queue', icon: Inbox, href: '/queue', badge: 'urgent' },
      { id: 'content', label: 'Content Review', icon: FileEdit, href: '/content', badge: 'pending' },
      { id: 'published', label: 'Published', icon: Send, href: '/published' },
    ],
  },
  {
    id: 'manage',
    label: 'Manage',
    items: [
      { id: 'projects', label: 'Projects', icon: FolderKanban, href: '/projects' },
      { id: 'accounts', label: 'Reddit Accounts', icon: Users, href: '/accounts' },
    ],
  },
  {
    id: 'admin',
    label: 'Admin',
    items: [
      { id: 'users', label: 'User Management', icon: UserCog, href: '/users', adminOnly: true },
    ],
  },
  {
    id: 'analyze',
    label: 'Analyze',
    items: [
      { id: 'analytics', label: 'Analytics', icon: BarChart3, href: '/analytics' },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebar } = useUIStore();
  const { user } = useAuthStore();
  const { data: stats } = useDashboardStats();

  const isAdmin = user?.role === 'admin';

  const getBadgeCount = (badge?: 'urgent' | 'pending'): number | undefined => {
    if (!stats) return undefined;
    if (badge === 'urgent') {
      return (stats.opportunities?.by_urgency?.critical || 0) + (stats.opportunities?.by_urgency?.high || 0);
    }
    if (badge === 'pending') {
      return stats.content?.pending_review || 0;
    }
    return undefined;
  };

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 h-screen border-r bg-sidebar transition-all duration-300',
        sidebarCollapsed ? 'w-16' : 'w-64'
      )}
    >
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center border-b px-4">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Zap className="h-5 w-5 text-primary-foreground" />
            </div>
            {!sidebarCollapsed && (
              <span className="font-semibold text-sidebar-foreground">Adkuu Platform</span>
            )}
          </Link>
        </div>

        {/* Navigation */}
        <ScrollArea className="flex-1 py-4">
          <nav className="space-y-6 px-2">
            {navigationGroups.map((group) => {
              // Filter items based on admin access
              const visibleItems = group.items.filter(
                (item) => !item.adminOnly || isAdmin
              );

              // Don't render group if no visible items
              if (visibleItems.length === 0) return null;

              return (
              <div key={group.id}>
                {group.label && !sidebarCollapsed && (
                  <h3 className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-sidebar-foreground/60">
                    {group.label}
                  </h3>
                )}
                <div className="space-y-1">
                  {visibleItems.map((item) => {
                    const isActive = pathname === item.href;
                    const badgeCount = getBadgeCount(item.badge);
                    const Icon = item.icon;

                    const navLink = (
                      <Link
                        key={item.id}
                        href={item.href}
                        className={cn(
                          'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                          isActive
                            ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                            : 'text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                          sidebarCollapsed && 'justify-center px-2'
                        )}
                      >
                        <Icon className="h-5 w-5 shrink-0" />
                        {!sidebarCollapsed && (
                          <>
                            <span className="flex-1">{item.label}</span>
                            {badgeCount !== undefined && badgeCount > 0 && (
                              <Badge
                                variant={item.badge === 'urgent' ? 'destructive' : 'secondary'}
                                className="ml-auto h-5 min-w-5 px-1.5"
                              >
                                {badgeCount > 99 ? '99+' : badgeCount}
                              </Badge>
                            )}
                          </>
                        )}
                      </Link>
                    );

                    if (sidebarCollapsed) {
                      return (
                        <Tooltip key={item.id} delayDuration={0}>
                          <TooltipTrigger asChild>{navLink}</TooltipTrigger>
                          <TooltipContent side="right" className="flex items-center gap-2">
                            {item.label}
                            {badgeCount !== undefined && badgeCount > 0 && (
                              <Badge
                                variant={item.badge === 'urgent' ? 'destructive' : 'secondary'}
                                className="h-5 min-w-5 px-1.5"
                              >
                                {badgeCount}
                              </Badge>
                            )}
                          </TooltipContent>
                        </Tooltip>
                      );
                    }

                    return navLink;
                  })}
                </div>
              </div>
            );
            })}
          </nav>
        </ScrollArea>

        {/* Settings & Collapse */}
        <div className="border-t p-2">
          {!sidebarCollapsed && (
            <Link
              href="/settings"
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                pathname === '/settings'
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                  : 'text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'
              )}
            >
              <Settings className="h-5 w-5" />
              <span>Settings</span>
            </Link>
          )}
          <Button
            variant="ghost"
            size="sm"
            className={cn('w-full', sidebarCollapsed ? 'px-2' : 'justify-start gap-3 px-3')}
            onClick={toggleSidebar}
          >
            {sidebarCollapsed ? (
              <ChevronRight className="h-5 w-5" />
            ) : (
              <>
                <ChevronLeft className="h-5 w-5" />
                <span>Collapse</span>
              </>
            )}
          </Button>
        </div>
      </div>
    </aside>
  );
}
