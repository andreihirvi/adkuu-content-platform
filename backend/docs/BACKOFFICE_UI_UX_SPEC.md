# Reddit Content Platform - Backoffice UI/UX Specification v2

## Design Philosophy

**Workflow-First Design**: The platform is centered around a clear content marketing pipeline:
```
Discover → Generate → Review → Publish → Track
```

Every UI decision should optimize for this workflow, making the most common paths frictionless.

**Key UX Principles:**
1. **Urgency-Aware**: Surface time-sensitive opportunities prominently
2. **Minimal Context Switching**: Complete tasks without leaving the current view
3. **Progressive Disclosure**: Show essential info first, details on demand
4. **Keyboard-First**: Power users can navigate entirely with keyboard
5. **Real-Time Feedback**: Instant updates on actions and background processes

---

## Tech Stack

### Core
| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 14.x | App Router, RSC support |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 3.4.x | Utility-first styling |
| shadcn/ui | Latest | Component library |

### State & Data
| Technology | Version | Purpose |
|------------|---------|---------|
| Zustand | 4.5.x | Global state management |
| TanStack Query | 5.x | Server state, caching, sync |
| better-auth | Latest | Authentication |

### Forms & Validation
| Technology | Version | Purpose |
|------------|---------|---------|
| React Hook Form | 7.x | Form handling |
| Zod | 3.x | Schema validation |

### UI Enhancements
| Technology | Version | Purpose |
|------------|---------|---------|
| Lucide React | Latest | Icons |
| Recharts | 2.x | Charts |
| Sonner | Latest | Toast notifications |
| cmdk | Latest | Command palette |

---

## Authentication with better-auth

### Server Setup (`lib/auth.ts`)

```typescript
import { betterAuth } from "better-auth"
import { Pool } from "pg"

export const auth = betterAuth({
  database: new Pool({
    connectionString: process.env.DATABASE_URL,
  }),

  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false, // Enable in production
  },

  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24, // Update session daily
    cookieCache: {
      enabled: true,
      maxAge: 60 * 5, // 5 minute client cache
    },
  },

  user: {
    additionalFields: {
      role: {
        type: "string",
        defaultValue: "user",
      },
    },
  },

  trustedOrigins: [
    process.env.NEXT_PUBLIC_APP_URL!,
  ],
})

export type Session = typeof auth.$Infer.Session
```

### API Route Handler (`app/api/auth/[...all]/route.ts`)

```typescript
import { auth } from "@/lib/auth"
import { toNextJsHandler } from "better-auth/next-js"

export const { GET, POST } = toNextJsHandler(auth)
```

### Client Setup (`lib/auth-client.ts`)

```typescript
import { createAuthClient } from "better-auth/react"

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_APP_URL,
})

// Export typed hooks
export const {
  signIn,
  signUp,
  signOut,
  useSession,
} = authClient
```

### Auth Provider (`components/providers/auth-provider.tsx`)

```typescript
"use client"

import { createContext, useContext, ReactNode } from "react"
import { useSession } from "@/lib/auth-client"
import type { Session } from "@/lib/auth"

interface AuthContextType {
  session: Session | null
  isLoading: boolean
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const { data: session, isPending } = useSession()

  return (
    <AuthContext.Provider value={{
      session: session ?? null,
      isLoading: isPending,
      isAuthenticated: !!session,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error("useAuth must be used within AuthProvider")
  return context
}
```

### Auth Guard (`components/auth-guard.tsx`)

```typescript
"use client"

import { useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { useAuth } from "@/components/providers/auth-provider"
import { LoadingScreen } from "@/components/ui/loading-screen"

const PUBLIC_ROUTES = ["/login", "/register", "/forgot-password"]

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { isAuthenticated, isLoading } = useAuth()

  const isPublicRoute = PUBLIC_ROUTES.some(route => pathname?.startsWith(route))

  useEffect(() => {
    if (isLoading) return

    if (!isAuthenticated && !isPublicRoute) {
      router.push(`/login?redirect=${encodeURIComponent(pathname || "/")}`)
    } else if (isAuthenticated && isPublicRoute) {
      router.push("/")
    }
  }, [isAuthenticated, isLoading, isPublicRoute, pathname, router])

  if (isLoading) {
    return <LoadingScreen />
  }

  if (!isAuthenticated && !isPublicRoute) {
    return null
  }

  return <>{children}</>
}
```

### Middleware (`middleware.ts`)

```typescript
import { NextRequest, NextResponse } from "next/server"
import { betterFetch } from "@better-fetch/fetch"
import type { Session } from "@/lib/auth"

const PUBLIC_ROUTES = ["/login", "/register", "/forgot-password", "/api/auth"]

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Skip public routes and API
  if (PUBLIC_ROUTES.some(route => pathname.startsWith(route))) {
    return NextResponse.next()
  }

  // Check session
  const { data: session } = await betterFetch<Session>(
    "/api/auth/get-session",
    {
      baseURL: request.nextUrl.origin,
      headers: { cookie: request.headers.get("cookie") || "" },
    }
  )

  if (!session) {
    return NextResponse.redirect(
      new URL(`/login?redirect=${encodeURIComponent(pathname)}`, request.url)
    )
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)"],
}
```

---

## Navigation Architecture

### Primary Navigation Concept

The navigation follows a **hub-and-spoke model** where the Dashboard is the central hub, and each main section is a spoke. The most important workflow (Opportunities → Content → Published) is emphasized.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              NAVIGATION STRUCTURE                             │
└──────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │  DASHBOARD  │  ← Central Hub
                              │   (Home)    │
                              └──────┬──────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
          ▼                          ▼                          ▼
   ┌─────────────┐           ┌─────────────┐           ┌─────────────┐
   │   WORKFLOW  │           │   MANAGE    │           │   ANALYZE   │
   │             │           │             │           │             │
   │ • Queue     │           │ • Projects  │           │ • Analytics │
   │ • Content   │           │ • Accounts  │           │ • Insights  │
   │ • Published │           │ • Settings  │           │             │
   └─────────────┘           └─────────────┘           └─────────────┘
        ↑
        │ MAIN WORKFLOW PATH
        │ (Emphasized in UI)
```

### Sidebar Design

**Compact Icon Sidebar** (56px) with tooltips - matching adkuu-backoffice pattern but with workflow grouping.

```typescript
// Sidebar navigation items
const navigationGroups = [
  {
    id: "main",
    items: [
      {
        id: "dashboard",
        label: "Dashboard",
        icon: LayoutDashboard,
        href: "/"
      },
    ],
  },
  {
    id: "workflow",
    label: "Workflow",
    items: [
      {
        id: "queue",
        label: "Opportunity Queue",
        icon: Inbox,
        href: "/queue",
        badge: "urgentCount", // Dynamic badge showing urgent count
      },
      {
        id: "content",
        label: "Content Review",
        icon: FileEdit,
        href: "/content",
        badge: "pendingContentCount",
      },
      {
        id: "published",
        label: "Published",
        icon: Send,
        href: "/published",
      },
    ],
  },
  {
    id: "manage",
    label: "Manage",
    items: [
      {
        id: "projects",
        label: "Projects",
        icon: FolderKanban,
        href: "/projects",
      },
      {
        id: "accounts",
        label: "Reddit Accounts",
        icon: Users,
        href: "/accounts",
      },
    ],
  },
  {
    id: "analyze",
    label: "Analyze",
    items: [
      {
        id: "analytics",
        label: "Analytics",
        icon: BarChart3,
        href: "/analytics",
      },
    ],
  },
]

const bottomNavItems = [
  {
    id: "settings",
    label: "Settings",
    icon: Settings,
    href: "/settings",
  },
]
```

### Visual Sidebar Layout

```
┌────────────────┐
│   [Logo]       │  ← Brand icon, links to dashboard
├────────────────┤
│                │
│   [Dashboard]  │  ← Always visible
│                │
│   ─────────────│  ← Separator
│                │
│   [Queue] (5)  │  ← Badge shows urgent count
│   [Content](3) │  ← Badge shows pending count
│   [Published]  │
│                │
│   ─────────────│
│                │
│   [Projects]   │
│   [Accounts]   │
│                │
│   ─────────────│
│                │
│   [Analytics]  │
│                │
│                │
│       ↓        │
│   (spacer)     │
│       ↓        │
│                │
│   [Settings]   │
│   [User Menu]  │
└────────────────┘
```

### Header Design

Simpler than adkuu-backoffice since we have single-tenant (no company switching needed initially).

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  [Project: AI Coding Blog ▼]     [⌘K Search]              [🔔] [User ▼]     │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Components:**
- **Project Selector**: Quick switch between projects (filters all data)
- **Command Palette Trigger**: `⌘K` to open global search
- **Notifications**: Bell icon with badge for alerts
- **User Menu**: Profile, settings, logout

---

## Page Structure

### 1. Dashboard (`/`)

**Purpose:** Quick overview and entry point to urgent tasks.

**Layout Sections:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  🔥 URGENT ACTIONS (Collapsible, expanded by default)                   │ │
│ │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐         │ │
│ │  │ ⚡ 3 Urgent Opps │ │ 📝 5 Pending     │ │ ⚠️ 1 Account     │         │ │
│ │  │ Window closing   │ │ Content to      │ │ Rate Limited    │         │ │
│ │  │ [View Queue →]   │ │ review          │ │ [Check →]       │         │ │
│ │  └──────────────────┘ └──────────────────┘ └──────────────────┘         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│ ┌─────────────────────────────────┐ ┌─────────────────────────────────────┐ │
│ │  TODAY'S STATS                  │ │  PERFORMANCE (7 DAYS)               │ │
│ │  ┌────┐ ┌────┐ ┌────┐ ┌────┐   │ │  [Area chart: Score over time]      │ │
│ │  │ 12 │ │  5 │ │  3 │ │ 47 │   │ │                                      │ │
│ │  │Disc│ │Gen │ │Pub │ │Avg │   │ │                                      │ │
│ │  └────┘ └────┘ └────┘ └────┘   │ │                                      │ │
│ └─────────────────────────────────┘ └─────────────────────────────────────┘ │
│                                                                              │
│ ┌─────────────────────────────────┐ ┌─────────────────────────────────────┐ │
│ │  RECENT OPPORTUNITIES           │ │  TOP PERFORMERS                     │ │
│ │  [Compact list with quick act.] │ │  [Table of best content]            │ │
│ └─────────────────────────────────┘ └─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Urgent actions bar is dismissible but reappears when new urgent items arrive
- Stats cards are clickable, navigate to relevant section
- Recent opportunities support inline actions (approve, generate)
- Performance chart has period selector (7d, 30d, 90d)

---

### 2. Opportunity Queue (`/queue`)

**Purpose:** Primary workflow screen for processing opportunities.

**Design Philosophy:**
- Split-pane view: List on left, detail on right
- List shows enough info to make quick decisions
- Detail view allows deeper analysis without leaving page

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  Opportunity Queue                                                  [⟳ Refresh]│
├────────────────────────────────────────────────────────────────────────────────┤
│  Filters: [Urgency ▼] [Subreddit ▼] [Score: 0.5+ ▼] [Status ▼]    [Clear All] │
├──────────────────────────────┬─────────────────────────────────────────────────┤
│                              │                                                  │
│  ┌────────────────────────┐  │  SELECTED OPPORTUNITY                           │
│  │ 🔴 URGENT    0.89     │←─│  ──────────────────────────────────────────────  │
│  │ r/programming • 45m   │  │                                                  │
│  │ "Frustrated with..."  │  │  r/programming • Posted 45 min ago              │
│  │ ⚡ 156/hr • 🕐 45min  │  │  by u/developer123                               │
│  └────────────────────────┘  │                                                  │
│                              │  ┌────────────────────────────────────────────┐ │
│  ┌────────────────────────┐  │  │ "Frustrated with GitHub Copilot            │ │
│  │ 🟠 HIGH      0.76     │  │  │ suggestions in React hooks. Anyone found   │ │
│  │ r/learnprog • 1.5h    │  │  │ better alternatives or workarounds?"       │ │
│  │ "Best way to learn..."│  │  │                                             │ │
│  │ ⚡ 45/hr • 🕐 2.5hr   │  │  │ [Full post body if available...]            │ │
│  └────────────────────────┘  │  └────────────────────────────────────────────┘ │
│                              │                                                  │
│  ┌────────────────────────┐  │  ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │ 🟡 MEDIUM    0.58     │  │  │ Score: 0.89 │ │ ⚡ 156/hr   │ │ 🕐 ~45min │ │
│  │ r/webdev • 3h         │  │  │ ████████░░  │ │ Rising fast │ │ Window    │ │
│  │ "React vs Vue..."     │  │  └─────────────┘ └─────────────┘ └───────────┘ │
│  └────────────────────────┘  │                                                  │
│                              │  SCORE BREAKDOWN                                 │
│  ┌────────────────────────┐  │  Relevance  ████████░░ 0.92                     │
│  │ 🟢 LOW       0.42     │  │  Virality   ████████░░ 0.85                     │
│  │ r/coding • 5h         │  │  Timing     █████████░ 0.95                     │
│  │ "Simple question..."  │  │                                                  │
│  └────────────────────────┘  │  ──────────────────────────────────────────────  │
│                              │                                                  │
│                              │  ACTIONS                                         │
│                              │  ┌─────────────────────────────────────────────┐│
│                              │  │[Generate ▼] [Skip] [Snooze ▼] [View Post ↗]││
│                              │  └─────────────────────────────────────────────┘│
│                              │                                                  │
│  ──────────────────────────  │  ──────────────────────────────────────────────  │
│  Showing 4 of 23            │                                                  │
│  [Load More]                 │  GENERATED CONTENT (if exists)                  │
│                              │  ┌─────────────────────────────────────────────┐│
│                              │  │ Status: Pending Review                      ││
│                              │  │ [View Content →]                            ││
│                              │  └─────────────────────────────────────────────┘│
└──────────────────────────────┴─────────────────────────────────────────────────┘
```

**Key Interactions:**
- Click opportunity in list → Shows in detail pane
- Keyboard: `j/k` to navigate list, `g` to generate, `s` to skip
- Generate dropdown shows style options
- Snooze dropdown: 1h, 2h, 4h, 24h
- After action, auto-advance to next opportunity

---

### 3. Content Review (`/content`)

**Purpose:** Review, edit, and approve generated content before publishing.

**Split-pane design with live preview:**

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  Content Review                                                     [Filters ▼]│
├──────────────────────────────┬─────────────────────────────────────────────────┤
│                              │                                                  │
│  PENDING (5)                 │  CONTENT DETAIL                                 │
│  ┌────────────────────────┐  │                                                  │
│  │ ✅ Quality: 8.2       │←─│  For: r/programming                              │
│  │ r/programming          │  │  "Frustrated with GitHub Copilot..."            │
│  │ Helpful Expert • 187w  │  │  Quality: ████████░░ 8.2/10                     │
│  └────────────────────────┘  │                                                  │
│                              │  ┌──────────────────────┬───────────────────────┐│
│  ┌────────────────────────┐  │  │ EDIT                 │ PREVIEW              ││
│  │ ⚠️ Quality: 6.1       │  │  ├──────────────────────┼───────────────────────┤│
│  │ r/learnprogramming     │  │  │                      │                       ││
│  │ Casual • 145w          │  │  │ Been there! Here's   │ [Reddit-style         ││
│  │ Warning: Promotional   │  │  │ what worked for me:  │  comment preview      ││
│  └────────────────────────┘  │  │                      │  with proper          ││
│                              │  │ 1. **Be explicit...  │  markdown rendering]  ││
│  ┌────────────────────────┐  │  │                      │                       ││
│  │ ✅ Quality: 7.8       │  │  │ 2. **Custom inst...  │                       ││
│  │ r/webdev               │  │  │                      │                       ││
│  │ Technical • 210w       │  │  │ [Link to article]    │                       ││
│  └────────────────────────┘  │  │                      │                       ││
│                              │  └──────────────────────┴───────────────────────┘│
│                              │                                                  │
│                              │  QUALITY CHECKS                                  │
│                              │  ✅ Spam: 0.05   ✅ Promo: 0.12   ✅ Length     │
│                              │  ✅ Readability: 0.78   ✅ Authenticity: 0.85   │
│                              │                                                  │
│                              │  OPTIONS                                         │
│                              │  [✓] Include tracking link                      │
│                              │  Account: [u/ai_helper_bot ▼]                   │
│                              │                                                  │
│                              │  ┌─────────────────────────────────────────────┐│
│                              │  │ [Regenerate] [Reject]     [Approve & Publish]││
│                              │  └─────────────────────────────────────────────┘│
└──────────────────────────────┴─────────────────────────────────────────────────┘
```

**Key Features:**
- Side-by-side edit and preview
- Real-time preview updates as you type
- Quality checks shown inline
- Account selector for multi-account publishing
- Regenerate opens dialog with style/feedback options

---

### 4. Published Content (`/published`)

**Purpose:** Track performance of published content.

**Table view with expandable rows:**

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  Published Content                              Period: [Last 30 days ▼]       │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────┬──────────────────────────────────┬──────────┬───────┬───────┬───────┐│
│  │Score│ Content                          │Subreddit │ When  │Clicks │Status ││
│  ├─────┼──────────────────────────────────┼──────────┼───────┼───────┼───────┤│
│  │ ↑127│ "Been there! Here's what..."    │r/prog    │ 2d    │  23   │  ✅   ││
│  ├─────┴──────────────────────────────────┴──────────┴───────┴───────┴───────┤│
│  │ ▼ EXPANDED ROW                                                            ││
│  │ ┌──────────────────────────────────────────────────────────────────────┐  ││
│  │ │ Performance Chart │ Replies (8)                                      │  ││
│  │ │ [Mini sparkline]  │ "Thanks, this helped!" ↑12                       │  ││
│  │ │                   │ "Great advice" ↑8                                │  ││
│  │ │ Peak: +45/hr      │                                                  │  ││
│  │ │ Current: +2/hr    │ [View on Reddit ↗]                               │  ││
│  │ └──────────────────────────────────────────────────────────────────────┘  ││
│  ├─────┬──────────────────────────────────┬──────────┬───────┬───────┬───────┤│
│  │ ↑ 89│ "Great question! When I..."     │r/learn   │ 3d    │  15   │  ✅   ││
│  ├─────┼──────────────────────────────────┼──────────┼───────┼───────┼───────┤│
│  │ ↑ 45│ "I've been using a similar..."  │r/webdev  │ 5d    │   8   │  ✅   ││
│  ├─────┼──────────────────────────────────┼──────────┼───────┼───────┼───────┤│
│  │ ↓ -3│ "Check out this article..."     │r/prog    │ 1w    │   2   │  ⚠️   ││
│  ├─────┼──────────────────────────────────┼──────────┼───────┼───────┼───────┤│
│  │ 🗑️  │ "Here's a great resource..."    │r/learn   │ 1w    │   0   │  ❌   ││
│  └─────┴──────────────────────────────────┴──────────┴───────┴───────┴───────┘│
│                                                                                 │
│  [← Previous]  Page 1 of 5  [Next →]                                           │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

### 5. Projects (`/projects`)

**Card-based grid for project overview:**

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  Projects                                                   [+ New Project]    │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐              │
│  │ AI Coding Blog         ✅   │  │ SaaS Product Launch    ⏸️   │              │
│  │                             │  │                             │              │
│  │ 5 subreddits • 2 accounts   │  │ 3 subreddits • 1 account    │              │
│  │                             │  │                             │              │
│  │ This Week:                  │  │ This Week:                  │              │
│  │ 47 opps • 12 published      │  │ 12 opps • 3 published       │              │
│  │ Avg score: 45               │  │ Avg score: 28               │              │
│  │                             │  │                             │              │
│  │ ──────────────────────────  │  │ ──────────────────────────  │              │
│  │ [Mini performance chart]    │  │ [Mini performance chart]    │              │
│  │                             │  │                             │              │
│  │ [Configure]     [View Queue]│  │ [Configure]      [Resume]   │              │
│  └─────────────────────────────┘  └─────────────────────────────┘              │
│                                                                                 │
│  ┌─────────────────────────────┐                                               │
│  │         + New Project       │                                               │
│  │                             │                                               │
│  │    Click to create a new    │                                               │
│  │    project and start        │                                               │
│  │    discovering opportunities│                                               │
│  │                             │                                               │
│  └─────────────────────────────┘                                               │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
src/
├── app/
│   ├── (auth)/                    # Auth group (no layout)
│   │   ├── login/page.tsx
│   │   ├── register/page.tsx
│   │   └── forgot-password/page.tsx
│   │
│   ├── (dashboard)/               # Main app group (with layout)
│   │   ├── layout.tsx             # Sidebar + Header layout
│   │   ├── page.tsx               # Dashboard (/)
│   │   │
│   │   ├── queue/
│   │   │   └── page.tsx           # Opportunity queue
│   │   │
│   │   ├── content/
│   │   │   ├── page.tsx           # Content list
│   │   │   └── [id]/page.tsx      # Content detail (optional)
│   │   │
│   │   ├── published/
│   │   │   ├── page.tsx           # Published list
│   │   │   └── [id]/page.tsx      # Published detail
│   │   │
│   │   ├── projects/
│   │   │   ├── page.tsx           # Projects list
│   │   │   ├── new/page.tsx       # New project
│   │   │   └── [id]/
│   │   │       ├── page.tsx       # Project settings
│   │   │       ├── subreddits/page.tsx
│   │   │       └── accounts/page.tsx
│   │   │
│   │   ├── accounts/
│   │   │   ├── page.tsx           # Reddit accounts list
│   │   │   └── [id]/page.tsx      # Account detail
│   │   │
│   │   ├── analytics/
│   │   │   └── page.tsx           # Analytics dashboard
│   │   │
│   │   └── settings/
│   │       └── page.tsx           # App settings
│   │
│   ├── api/
│   │   └── auth/
│   │       └── [...all]/route.ts  # better-auth handler
│   │
│   ├── layout.tsx                 # Root layout (providers)
│   └── globals.css
│
├── components/
│   ├── ui/                        # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   ├── dropdown-menu.tsx
│   │   ├── form.tsx
│   │   ├── input.tsx
│   │   ├── select.tsx
│   │   ├── table.tsx
│   │   ├── tabs.tsx
│   │   ├── toast.tsx
│   │   ├── tooltip.tsx
│   │   └── [...40+ components]
│   │
│   ├── layout/
│   │   ├── sidebar.tsx
│   │   ├── header.tsx
│   │   ├── app-layout.tsx
│   │   └── page-header.tsx
│   │
│   ├── providers/
│   │   ├── auth-provider.tsx
│   │   ├── query-provider.tsx
│   │   └── providers.tsx          # Combined providers
│   │
│   ├── features/                  # Feature-specific components
│   │   ├── dashboard/
│   │   │   ├── urgent-actions.tsx
│   │   │   ├── stats-cards.tsx
│   │   │   ├── performance-chart.tsx
│   │   │   └── recent-opportunities.tsx
│   │   │
│   │   ├── opportunities/
│   │   │   ├── opportunity-list.tsx
│   │   │   ├── opportunity-card.tsx
│   │   │   ├── opportunity-detail.tsx
│   │   │   ├── urgency-badge.tsx
│   │   │   ├── score-breakdown.tsx
│   │   │   ├── filters.tsx
│   │   │   └── actions.tsx
│   │   │
│   │   ├── content/
│   │   │   ├── content-list.tsx
│   │   │   ├── content-card.tsx
│   │   │   ├── content-editor.tsx
│   │   │   ├── content-preview.tsx
│   │   │   ├── quality-gates.tsx
│   │   │   └── regenerate-dialog.tsx
│   │   │
│   │   ├── published/
│   │   │   ├── published-table.tsx
│   │   │   ├── performance-row.tsx
│   │   │   └── performance-chart.tsx
│   │   │
│   │   ├── projects/
│   │   │   ├── project-card.tsx
│   │   │   ├── project-form.tsx
│   │   │   ├── subreddit-manager.tsx
│   │   │   └── keyword-editor.tsx
│   │   │
│   │   ├── accounts/
│   │   │   ├── account-card.tsx
│   │   │   ├── account-health.tsx
│   │   │   └── oauth-button.tsx
│   │   │
│   │   └── analytics/
│   │       ├── metric-card.tsx
│   │       ├── time-series-chart.tsx
│   │       └── subreddit-table.tsx
│   │
│   ├── shared/                    # Shared/common components
│   │   ├── loading-screen.tsx
│   │   ├── empty-state.tsx
│   │   ├── error-boundary.tsx
│   │   ├── confirm-dialog.tsx
│   │   ├── data-table.tsx
│   │   ├── pagination.tsx
│   │   └── kbd.tsx                # Keyboard shortcut display
│   │
│   └── auth-guard.tsx
│
├── lib/
│   ├── auth.ts                    # better-auth server config
│   ├── auth-client.ts             # better-auth client
│   ├── api-client.ts              # Axios wrapper
│   ├── utils.ts                   # Utility functions
│   └── constants.ts
│
├── stores/
│   ├── ui-store.ts                # UI state (sidebar, modals)
│   ├── project-store.ts           # Selected project, project data
│   ├── opportunity-store.ts       # Opportunity queue state
│   ├── content-store.ts           # Content review state
│   └── filters-store.ts           # Shared filter state
│
├── hooks/
│   ├── use-opportunities.ts       # TanStack Query hook
│   ├── use-content.ts
│   ├── use-projects.ts
│   ├── use-accounts.ts
│   ├── use-analytics.ts
│   ├── use-keyboard.ts            # Keyboard shortcuts
│   └── use-realtime.ts            # WebSocket/polling
│
├── types/
│   ├── index.ts                   # Re-exports
│   ├── api.ts                     # API response types
│   ├── opportunity.ts
│   ├── content.ts
│   ├── project.ts
│   └── account.ts
│
└── middleware.ts
```

---

## Zustand Stores Design

### Core Principle: Separation of Concerns

- **UI Store**: Only UI state (sidebar collapsed, active modals)
- **Domain Stores**: Business logic state, derived from server data
- **TanStack Query**: Server state, caching, synchronization

### UI Store (`stores/ui-store.ts`)

```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface UIState {
  // Sidebar
  sidebarCollapsed: boolean
  toggleSidebar: () => void

  // Command palette
  commandPaletteOpen: boolean
  openCommandPalette: () => void
  closeCommandPalette: () => void

  // Modals
  activeModal: string | null
  modalData: unknown
  openModal: (id: string, data?: unknown) => void
  closeModal: () => void

  // Notifications panel
  notificationsPanelOpen: boolean
  toggleNotificationsPanel: () => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

      commandPaletteOpen: false,
      openCommandPalette: () => set({ commandPaletteOpen: true }),
      closeCommandPalette: () => set({ commandPaletteOpen: false }),

      activeModal: null,
      modalData: null,
      openModal: (id, data) => set({ activeModal: id, modalData: data }),
      closeModal: () => set({ activeModal: null, modalData: null }),

      notificationsPanelOpen: false,
      toggleNotificationsPanel: () => set((s) => ({
        notificationsPanelOpen: !s.notificationsPanelOpen
      })),
    }),
    { name: 'ui-store' }
  )
)
```

### Project Store (`stores/project-store.ts`)

```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ProjectState {
  // Selected project (persisted)
  selectedProjectId: string | null
  setSelectedProject: (id: string | null) => void

  // Quick access to project data (populated by query)
  projectsMap: Map<string, Project>
  setProjectsMap: (projects: Project[]) => void
  getProject: (id: string) => Project | undefined
  getSelectedProject: () => Project | undefined
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set, get) => ({
      selectedProjectId: null,
      setSelectedProject: (id) => set({ selectedProjectId: id }),

      projectsMap: new Map(),
      setProjectsMap: (projects) => set({
        projectsMap: new Map(projects.map(p => [p.id, p]))
      }),
      getProject: (id) => get().projectsMap.get(id),
      getSelectedProject: () => {
        const { selectedProjectId, projectsMap } = get()
        return selectedProjectId ? projectsMap.get(selectedProjectId) : undefined
      },
    }),
    {
      name: 'project-store',
      partialize: (state) => ({ selectedProjectId: state.selectedProjectId })
    }
  )
)
```

### Opportunity Store (`stores/opportunity-store.ts`)

```typescript
import { create } from 'zustand'

interface OpportunityFilters {
  urgency: ('URGENT' | 'HIGH' | 'MEDIUM' | 'LOW')[]
  subreddits: string[]
  minScore: number
  status: string[]
  includeExpired: boolean
}

interface OpportunityState {
  // Filters
  filters: OpportunityFilters
  setFilter: <K extends keyof OpportunityFilters>(
    key: K,
    value: OpportunityFilters[K]
  ) => void
  resetFilters: () => void

  // Selection
  selectedOpportunityId: string | null
  setSelectedOpportunity: (id: string | null) => void

  // Optimistic updates tracking
  processingIds: Set<string>
  addProcessing: (id: string) => void
  removeProcessing: (id: string) => void
}

const defaultFilters: OpportunityFilters = {
  urgency: [],
  subreddits: [],
  minScore: 0,
  status: ['PENDING'],
  includeExpired: false,
}

export const useOpportunityStore = create<OpportunityState>((set, get) => ({
  filters: defaultFilters,
  setFilter: (key, value) => set((s) => ({
    filters: { ...s.filters, [key]: value }
  })),
  resetFilters: () => set({ filters: defaultFilters }),

  selectedOpportunityId: null,
  setSelectedOpportunity: (id) => set({ selectedOpportunityId: id }),

  processingIds: new Set(),
  addProcessing: (id) => set((s) => ({
    processingIds: new Set([...s.processingIds, id])
  })),
  removeProcessing: (id) => set((s) => {
    const next = new Set(s.processingIds)
    next.delete(id)
    return { processingIds: next }
  }),
}))
```

### Content Store (`stores/content-store.ts`)

```typescript
import { create } from 'zustand'

interface ContentState {
  // Filters
  filters: {
    status: string[]
    style: string[]
    minQuality: number
  }
  setFilter: (key: string, value: unknown) => void

  // Selection
  selectedContentId: string | null
  setSelectedContent: (id: string | null) => void

  // Editor state
  editedContent: string | null
  setEditedContent: (content: string | null) => void
  hasUnsavedChanges: boolean

  // Publishing
  publishingIds: Set<string>
}

export const useContentStore = create<ContentState>((set, get) => ({
  filters: {
    status: ['PENDING'],
    style: [],
    minQuality: 0,
  },
  setFilter: (key, value) => set((s) => ({
    filters: { ...s.filters, [key]: value }
  })),

  selectedContentId: null,
  setSelectedContent: (id) => set({
    selectedContentId: id,
    editedContent: null,
    hasUnsavedChanges: false,
  }),

  editedContent: null,
  setEditedContent: (content) => set({
    editedContent: content,
    hasUnsavedChanges: true,
  }),
  get hasUnsavedChanges() {
    return get().editedContent !== null
  },

  publishingIds: new Set(),
}))
```

---

## TanStack Query Hooks

### Opportunities Hook (`hooks/use-opportunities.ts`)

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { useOpportunityStore } from '@/stores/opportunity-store'
import { useProjectStore } from '@/stores/project-store'

export function useOpportunities() {
  const { selectedProjectId } = useProjectStore()
  const { filters } = useOpportunityStore()

  return useQuery({
    queryKey: ['opportunities', selectedProjectId, filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (selectedProjectId) params.set('project_id', selectedProjectId)
      if (filters.urgency.length) params.set('urgency', filters.urgency.join(','))
      if (filters.subreddits.length) params.set('subreddit', filters.subreddits.join(','))
      if (filters.minScore) params.set('min_score', filters.minScore.toString())
      if (filters.status.length) params.set('status', filters.status.join(','))
      params.set('include_expired', filters.includeExpired.toString())

      const { data } = await apiClient.get(`/opportunities?${params}`)
      return data
    },
    enabled: !!selectedProjectId,
    refetchInterval: 60000, // Refetch every minute
  })
}

export function useOpportunity(id: string | null) {
  return useQuery({
    queryKey: ['opportunity', id],
    queryFn: async () => {
      const { data } = await apiClient.get(`/opportunities/${id}`)
      return data
    },
    enabled: !!id,
  })
}

export function useGenerateContent() {
  const queryClient = useQueryClient()
  const { addProcessing, removeProcessing } = useOpportunityStore()

  return useMutation({
    mutationFn: async ({
      opportunityId,
      style
    }: {
      opportunityId: string
      style: string
    }) => {
      addProcessing(opportunityId)
      const { data } = await apiClient.post(
        `/opportunities/${opportunityId}/generate-content`,
        { style }
      )
      return data
    },
    onSuccess: (_, { opportunityId }) => {
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
      queryClient.invalidateQueries({ queryKey: ['opportunity', opportunityId] })
      queryClient.invalidateQueries({ queryKey: ['content'] })
    },
    onSettled: (_, __, { opportunityId }) => {
      removeProcessing(opportunityId)
    },
  })
}

export function useSkipOpportunity() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (opportunityId: string) => {
      const { data } = await apiClient.post(
        `/opportunities/${opportunityId}/reject`,
        { reason: 'Skipped by user' }
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
    },
  })
}
```

---

## Reusable Components Library

### Core UI Components (shadcn/ui)

Install these via `npx shadcn-ui@latest add`:

```bash
npx shadcn-ui@latest add button card dialog dropdown-menu form input label
npx shadcn-ui@latest add select tabs table toast tooltip badge separator
npx shadcn-ui@latest add avatar popover command scroll-area skeleton switch
npx shadcn-ui@latest add alert alert-dialog aspect-ratio checkbox collapsible
npx shadcn-ui@latest add context-menu hover-card menubar navigation-menu
npx shadcn-ui@latest add progress radio-group resizable sheet slider sonner
npx shadcn-ui@latest add textarea toggle toggle-group
```

### Custom Reusable Components

#### UrgencyBadge

```typescript
// components/shared/urgency-badge.tsx
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { Urgency } from '@/types'

const urgencyConfig: Record<Urgency, { label: string; className: string }> = {
  URGENT: { label: 'Urgent', className: 'bg-red-500 text-white animate-pulse' },
  HIGH: { label: 'High', className: 'bg-orange-500 text-white' },
  MEDIUM: { label: 'Medium', className: 'bg-yellow-500 text-black' },
  LOW: { label: 'Low', className: 'bg-gray-400 text-white' },
}

export function UrgencyBadge({ urgency }: { urgency: Urgency }) {
  const config = urgencyConfig[urgency]
  return (
    <Badge className={cn('font-semibold', config.className)}>
      {config.label}
    </Badge>
  )
}
```

#### ScoreBar

```typescript
// components/shared/score-bar.tsx
import { cn } from '@/lib/utils'

interface ScoreBarProps {
  value: number  // 0-1
  label?: string
  showValue?: boolean
  size?: 'sm' | 'md' | 'lg'
  colorScale?: 'default' | 'quality'
}

export function ScoreBar({
  value,
  label,
  showValue = true,
  size = 'md',
  colorScale = 'default'
}: ScoreBarProps) {
  const percentage = Math.round(value * 100)

  const getColor = () => {
    if (colorScale === 'quality') {
      if (value >= 0.7) return 'bg-green-500'
      if (value >= 0.5) return 'bg-yellow-500'
      return 'bg-red-500'
    }
    return 'bg-primary'
  }

  const heights = { sm: 'h-1.5', md: 'h-2', lg: 'h-3' }

  return (
    <div className="space-y-1">
      {(label || showValue) && (
        <div className="flex justify-between text-sm">
          {label && <span className="text-muted-foreground">{label}</span>}
          {showValue && <span className="font-medium">{value.toFixed(2)}</span>}
        </div>
      )}
      <div className={cn('w-full bg-muted rounded-full', heights[size])}>
        <div
          className={cn('rounded-full transition-all', heights[size], getColor())}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}
```

#### StatCard

```typescript
// components/shared/stat-card.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { LucideIcon } from 'lucide-react'

interface StatCardProps {
  title: string
  value: string | number
  subtitle?: string
  trend?: number  // percentage change
  icon?: LucideIcon
  onClick?: () => void
}

export function StatCard({
  title,
  value,
  subtitle,
  trend,
  icon: Icon,
  onClick
}: StatCardProps) {
  return (
    <Card
      className={cn(
        'transition-shadow',
        onClick && 'cursor-pointer hover:shadow-md'
      )}
      onClick={onClick}
    >
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {(subtitle || trend !== undefined) && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {trend !== undefined && (
              <span className={cn(
                trend > 0 ? 'text-green-600' : trend < 0 ? 'text-red-600' : ''
              )}>
                {trend > 0 ? '↑' : trend < 0 ? '↓' : '→'} {Math.abs(trend)}%
              </span>
            )}
            {subtitle && <span>{subtitle}</span>}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
```

#### EmptyState

```typescript
// components/shared/empty-state.tsx
import { LucideIcon, FileQuestion } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description: string
  action?: {
    label: string
    onClick: () => void
  }
}

export function EmptyState({
  icon: Icon = FileQuestion,
  title,
  description,
  action
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="rounded-full bg-muted p-4 mb-4">
        <Icon className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-sm mt-1">
        {description}
      </p>
      {action && (
        <Button onClick={action.onClick} className="mt-4">
          {action.label}
        </Button>
      )}
    </div>
  )
}
```

#### PageHeader

```typescript
// components/layout/page-header.tsx
import { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  description?: string
  actions?: ReactNode
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        {description && (
          <p className="text-muted-foreground">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}
```

#### SplitPane

```typescript
// components/shared/split-pane.tsx
import { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface SplitPaneProps {
  left: ReactNode
  right: ReactNode
  leftWidth?: string  // Tailwind width class
  className?: string
}

export function SplitPane({
  left,
  right,
  leftWidth = 'w-1/3',
  className
}: SplitPaneProps) {
  return (
    <div className={cn('flex gap-6 h-full', className)}>
      <div className={cn('flex-shrink-0 overflow-auto', leftWidth)}>
        {left}
      </div>
      <div className="flex-1 overflow-auto">
        {right}
      </div>
    </div>
  )
}
```

---

## Keyboard Shortcuts

Global shortcuts available throughout the app:

| Shortcut | Action |
|----------|--------|
| `⌘K` / `Ctrl+K` | Open command palette |
| `⌘/` / `Ctrl+/` | Open keyboard shortcuts help |
| `g then d` | Go to Dashboard |
| `g then q` | Go to Queue |
| `g then c` | Go to Content |
| `g then p` | Go to Published |

Queue-specific shortcuts:

| Shortcut | Action |
|----------|--------|
| `j` / `↓` | Next opportunity |
| `k` / `↑` | Previous opportunity |
| `g` | Generate content (opens style menu) |
| `s` | Skip opportunity |
| `z` | Snooze (opens time menu) |
| `Enter` | View opportunity detail |
| `o` | Open on Reddit |

Content-specific shortcuts:

| Shortcut | Action |
|----------|--------|
| `j` / `↓` | Next content |
| `k` / `↑` | Previous content |
| `e` | Edit content |
| `r` | Regenerate |
| `a` | Approve |
| `x` | Reject |
| `⌘Enter` | Approve & Publish |

---

## API Client (`lib/api-client.ts`)

```typescript
import axios, { AxiosInstance, AxiosError } from 'axios'
import { toast } from 'sonner'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

class APIClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: { 'Content-Type': 'application/json' },
      withCredentials: true, // For better-auth cookies
    })

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<{ detail?: string }>) => {
        const message = error.response?.data?.detail || 'An error occurred'

        // Don't toast on 401 (handled by auth)
        if (error.response?.status !== 401) {
          toast.error(message)
        }

        return Promise.reject(error)
      }
    )
  }

  async get<T>(url: string, params?: Record<string, unknown>) {
    const response = await this.client.get<T>(url, { params })
    return response.data
  }

  async post<T>(url: string, data?: unknown) {
    const response = await this.client.post<T>(url, data)
    return response.data
  }

  async put<T>(url: string, data?: unknown) {
    const response = await this.client.put<T>(url, data)
    return response.data
  }

  async patch<T>(url: string, data?: unknown) {
    const response = await this.client.patch<T>(url, data)
    return response.data
  }

  async delete<T>(url: string) {
    const response = await this.client.delete<T>(url)
    return response.data
  }
}

export const apiClient = new APIClient()
```

---

## Summary

This UI/UX specification provides:

1. **better-auth Integration**: Complete setup for server, client, middleware, and components
2. **Workflow-Centric Navigation**: Hub-and-spoke model with emphasis on the main pipeline
3. **Split-Pane Layouts**: Master-detail views for Queue and Content pages
4. **Zustand Stores**: Clean separation between UI state, domain state, and server state
5. **TanStack Query**: Server state management with automatic caching and sync
6. **Reusable Components**: 10+ shared components for consistent UI
7. **Keyboard Shortcuts**: Power-user friendly navigation
8. **Modern Stack**: Next.js 14, shadcn/ui, Tailwind, TypeScript

The design prioritizes:
- **Speed**: Urgent opportunities surface immediately
- **Efficiency**: Complete workflows without context switching
- **Clarity**: Progressive disclosure of information
- **Power**: Keyboard shortcuts for power users
