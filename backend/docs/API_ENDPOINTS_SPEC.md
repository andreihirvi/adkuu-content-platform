# Reddit Content Platform - API Endpoints Specification

## Overview

This document details all API endpoints required for the Reddit Content Platform backoffice, indicating which endpoints already exist and which need to be implemented.

**Base URL:** `/api/v1`

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Exists - Ready to use |
| 🔧 | Exists - Needs extension |
| ❌ | Missing - Needs implementation |

---

## 1. Authentication

> **Note:** If using external SSO (like adkuu-backoffice), these endpoints may not be needed.

| Status | Method | Endpoint | Description |
|--------|--------|----------|-------------|
| ❌ | POST | `/auth/login` | User login with email/password |
| ❌ | POST | `/auth/register` | User registration |
| ❌ | POST | `/auth/logout` | Logout (invalidate token) |
| ❌ | GET | `/auth/me` | Get current user |
| ❌ | POST | `/auth/refresh` | Refresh JWT token |
| ❌ | POST | `/auth/forgot-password` | Request password reset |
| ❌ | POST | `/auth/reset-password` | Reset password with token |

### Implementation Details

#### POST `/auth/login`
```typescript
// Request
{
  email: string
  password: string
}

// Response 200
{
  access_token: string
  token_type: "bearer"
  expires_in: number  // seconds
  user: {
    id: string
    email: string
    name: string
    is_superuser: boolean
  }
}

// Response 401
{
  detail: "Invalid credentials"
}
```

#### GET `/auth/me`
```typescript
// Headers
Authorization: Bearer <token>

// Response 200
{
  id: string
  email: string
  name: string
  is_superuser: boolean
  created_at: string
}
```

---

## 2. Projects

| Status | Method | Endpoint | Description |
|--------|--------|----------|-------------|
| ✅ | GET | `/projects` | List all projects |
| ✅ | POST | `/projects` | Create project |
| 🔧 | GET | `/projects/{id}` | Get project with stats |
| ✅ | PUT | `/projects/{id}` | Update project |
| ✅ | DELETE | `/projects/{id}` | Archive project |
| ✅ | POST | `/projects/{id}/subreddits` | Add subreddit config |
| ✅ | GET | `/projects/{id}/subreddits` | List subreddit configs |
| ✅ | DELETE | `/projects/{id}/subreddits/{name}` | Remove subreddit |
| ❌ | PUT | `/projects/{id}/subreddits/{name}` | Update subreddit config |

### Extensions Needed

#### GET `/projects/{id}` - Add Stats
```typescript
// Current Response
{
  id: string
  name: string
  description: string
  // ...other fields
}

// Extended Response (add stats)
{
  id: string
  name: string
  description: string
  // ...other fields
  stats: {
    opportunities_pending: number
    opportunities_total_week: number
    content_pending: number
    content_published_week: number
    accounts_active: number
    avg_score: number
    last_activity_at: string | null
  }
}
```

#### PUT `/projects/{id}/subreddits/{name}` - NEW
```typescript
// Request
{
  daily_post_limit?: number
  is_active?: boolean
  priority?: number  // for ordering
}

// Response 200
{
  id: string
  subreddit_name: string
  daily_post_limit: number
  is_active: boolean
  priority: number
}
```

---

## 3. Opportunities

| Status | Method | Endpoint | Description |
|--------|--------|----------|-------------|
| ✅ | GET | `/opportunities` | List opportunities (filtered) |
| ✅ | GET | `/opportunities/{id}` | Get opportunity detail |
| ✅ | POST | `/opportunities/{id}/approve` | Approve for generation |
| ✅ | POST | `/opportunities/{id}/reject` | Reject with reason |
| ✅ | POST | `/opportunities/{id}/generate-content` | Generate content |
| ✅ | POST | `/opportunities/mine` | Trigger mining |
| ✅ | POST | `/opportunities/{id}/refresh` | Refresh scores |
| ❌ | POST | `/opportunities/{id}/snooze` | Snooze opportunity |
| ❌ | GET | `/opportunities/{id}/reddit-comments` | Get existing Reddit comments |

### Extensions Needed

#### GET `/opportunities` - Extended Filters
```typescript
// Query Parameters (existing)
project_id?: string
status?: string[]  // comma-separated
subreddit?: string
min_score?: number
include_expired?: boolean
limit?: number
offset?: number

// NEW Query Parameters
urgency?: string[]  // URGENT,HIGH,MEDIUM,LOW
max_age_hours?: number
sort_by?: 'score' | 'urgency' | 'discovered_at' | 'velocity'
sort_order?: 'asc' | 'desc'
```

#### POST `/opportunities/{id}/snooze` - NEW
```typescript
// Request
{
  hours: number  // 1, 2, 4, 8, 24
}

// Response 200
{
  id: string
  status: "SNOOZED"
  snoozed_until: string  // ISO datetime
}
```

#### GET `/opportunities/{id}/reddit-comments` - NEW
```typescript
// Response 200
{
  comments: [
    {
      id: string
      author: string
      author_karma: number
      body: string
      score: number
      created_at: string
      depth: number  // 0 = top-level
    }
  ]
  total: number
}
```

---

## 4. Content

| Status | Method | Endpoint | Description |
|--------|--------|----------|-------------|
| ✅ | GET | `/content` | List generated content |
| ✅ | GET | `/content/{id}` | Get content detail |
| ✅ | PUT | `/content/{id}` | Update content text |
| ✅ | POST | `/content/{id}/regenerate` | Regenerate with feedback |
| ✅ | POST | `/content/{id}/approve` | Approve for publishing |
| ✅ | POST | `/content/{id}/reject` | Reject content |
| ✅ | POST | `/content/{id}/publish` | Publish to Reddit |
| ✅ | GET | `/content/{id}/performance` | Get performance history |
| ❌ | GET | `/content/{id}/variants` | Get all content versions |
| ❌ | POST | `/content/{id}/preview` | Generate Reddit preview URL |

### Extensions Needed

#### POST `/content/{id}/regenerate` - Extend Request
```typescript
// Current Request
{
  feedback?: string
}

// Extended Request
{
  feedback?: string
  style?: 'HELPFUL_EXPERT' | 'CASUAL' | 'TECHNICAL' | 'STORYTELLING'
  max_length?: number
  include_link?: boolean
}
```

#### GET `/content/{id}/variants` - NEW
```typescript
// Response 200
{
  variants: [
    {
      id: string
      version: number
      content_text: string
      content_style: string
      quality_score: number
      created_at: string
      is_current: boolean
    }
  ]
}
```

#### GET `/content` - Extended Filters
```typescript
// NEW Query Parameters
style?: string[]  // HELPFUL_EXPERT,CASUAL,TECHNICAL,STORYTELLING
passed_quality?: boolean
min_quality_score?: number
sort_by?: 'created_at' | 'quality_score' | 'word_count'
```

---

## 5. Reddit Accounts

| Status | Method | Endpoint | Description |
|--------|--------|----------|-------------|
| ✅ | GET | `/accounts` | List accounts |
| ✅ | GET | `/accounts/{id}` | Get account detail |
| ✅ | PUT | `/accounts/{id}` | Update account settings |
| ✅ | DELETE | `/accounts/{id}` | Deactivate account |
| ✅ | POST | `/accounts/{id}/health-check` | Check account health |
| ✅ | POST | `/accounts/{id}/activate` | Activate account |
| ✅ | POST | `/accounts/{id}/deactivate` | Deactivate account |
| ✅ | GET | `/accounts/{id}/activity` | Get subreddit activity |
| ❌ | POST | `/accounts/{id}/assign-project` | Assign account to project |
| ❌ | DELETE | `/accounts/{id}/projects/{project_id}` | Remove from project |

### Extensions Needed

#### GET `/accounts` - Extended Response
```typescript
// Add to each account
{
  // ...existing fields
  projects: [
    {
      id: string
      name: string
      is_primary: boolean
    }
  ]
  recent_actions: [
    {
      action_type: 'COMMENT' | 'POST'
      subreddit: string
      created_at: string
      result: 'SUCCESS' | 'FAILED' | 'REMOVED'
    }
  ]
}
```

#### POST `/accounts/{id}/assign-project` - NEW
```typescript
// Request
{
  project_id: string
  is_primary?: boolean
  daily_limit?: number
}

// Response 200
{
  account_id: string
  project_id: string
  is_primary: boolean
  daily_limit: number
}
```

---

## 6. Reddit OAuth

| Status | Method | Endpoint | Description |
|--------|--------|----------|-------------|
| ✅ | GET | `/reddit/auth/url` | Get OAuth authorization URL |
| ✅ | GET | `/reddit/auth/callback` | OAuth callback handler |
| ✅ | POST | `/reddit/auth/refresh/{id}` | Refresh OAuth token |
| ❌ | POST | `/reddit/auth/revoke/{id}` | Revoke OAuth token |

### Details

#### GET `/reddit/auth/url`
```typescript
// Query Parameters
project_id?: string  // Optional: auto-assign to project after auth

// Response 200
{
  auth_url: string  // Reddit OAuth URL
  state: string     // For CSRF protection
}
```

#### GET `/reddit/auth/callback`
```typescript
// Query Parameters (from Reddit)
code: string
state: string

// Response 302 - Redirect to backoffice with success/error
// Redirect to: /accounts?status=connected&account=<username>
// Or: /accounts?error=<error_message>
```

---

## 7. Analytics

| Status | Method | Endpoint | Description |
|--------|--------|----------|-------------|
| ✅ | GET | `/analytics/projects/{id}/summary` | Project analytics summary |
| ✅ | GET | `/analytics/projects/{id}/performance` | Performance time series |
| ✅ | GET | `/analytics/subreddits/{name}/insights` | Subreddit insights |
| ✅ | GET | `/analytics/learning-features` | ML learning features |
| ✅ | GET | `/analytics/dashboard` | Dashboard summary |
| ❌ | GET | `/analytics/dashboard/urgent` | Urgent opportunities |
| ❌ | GET | `/analytics/dashboard/pipeline` | Content pipeline stats |
| ❌ | GET | `/analytics/dashboard/top-content` | Best performing content |
| ❌ | GET | `/analytics/content-styles` | Performance by content style |

### Extensions Needed

#### GET `/analytics/dashboard` - Extended Response
```typescript
// Response 200
{
  // Existing
  opportunities_pending: number
  content_pending: number
  published_today: number
  avg_score: number

  // NEW additions
  opportunities_urgent: number
  opportunities_high: number
  removal_rate_week: number
  total_clicks_week: number
  trend_vs_last_week: {
    opportunities: number  // percentage
    published: number
    score: number
  }
}
```

#### GET `/analytics/dashboard/urgent` - NEW
```typescript
// Query Parameters
limit?: number  // default 5

// Response 200
{
  opportunities: [
    {
      id: string
      post_title: string
      subreddit: string
      composite_score: number
      urgency: 'URGENT' | 'HIGH'
      estimated_window_minutes: number
      velocity: number
    }
  ]
}
```

#### GET `/analytics/dashboard/pipeline` - NEW
```typescript
// Response 200
{
  pipeline: {
    pending_opportunities: number
    approved_opportunities: number
    generating: number
    pending_review: number
    approved_content: number
    publishing: number
    published_today: number
    failed_today: number
  }
  conversion_rates: {
    opportunity_to_content: number
    content_to_approved: number
    approved_to_published: number
    published_to_successful: number  // score >= 10
  }
}
```

#### GET `/analytics/dashboard/top-content` - NEW
```typescript
// Query Parameters
period?: '7d' | '30d' | '90d'
limit?: number

// Response 200
{
  content: [
    {
      id: string
      content_text_preview: string  // first 100 chars
      subreddit: string
      score: number
      clicks: number
      published_at: string
      performance_trend: 'rising' | 'stable' | 'declining'
    }
  ]
}
```

#### GET `/analytics/content-styles` - NEW
```typescript
// Response 200
{
  styles: [
    {
      style: 'HELPFUL_EXPERT' | 'CASUAL' | 'TECHNICAL' | 'STORYTELLING'
      total_published: number
      avg_score: number
      removal_rate: number
      avg_quality_score: number
    }
  ]
}
```

---

## 8. Subreddit Analysis

| Status | Method | Endpoint | Description |
|--------|--------|----------|-------------|
| ❌ | POST | `/subreddits/analyze` | Analyze a subreddit |
| ❌ | GET | `/subreddits/{name}/rules` | Get subreddit rules |
| ❌ | GET | `/subreddits/{name}/stats` | Get subreddit stats |

### Implementation Details

#### POST `/subreddits/analyze` - NEW
```typescript
// Request
{
  subreddit_name: string  // without r/ prefix
}

// Response 200
{
  name: string
  display_name: string
  subscribers: number
  active_users: number
  posts_per_day: number
  type: 'public' | 'restricted' | 'private'

  size_category: 'small' | 'medium' | 'large' | 'massive'
  velocity_threshold: number

  requirements: {
    min_account_age_days: number | null
    min_karma: number | null
    min_comment_karma: number | null
    allows_links: boolean
    allows_self_promo: 'allowed' | 'limited' | 'banned'
  }

  rules_summary: string[]

  optimal_timing: {
    best_hours_utc: number[]
    best_days: number[]  // 0=Monday
  }

  relevance_topics: string[]
}

// Response 404
{
  detail: "Subreddit not found or is private"
}
```

#### GET `/subreddits/{name}/rules` - NEW
```typescript
// Response 200
{
  rules: [
    {
      title: string
      description: string
      applies_to: 'posts' | 'comments' | 'both'
    }
  ]
  self_promo_policy: string | null
  link_requirements: string | null
}
```

---

## 9. Settings

| Status | Method | Endpoint | Description |
|--------|--------|----------|-------------|
| ❌ | GET | `/settings` | Get user/global settings |
| ❌ | PUT | `/settings` | Update settings |
| ❌ | GET | `/settings/llm` | Get LLM configuration |
| ❌ | PUT | `/settings/llm` | Update LLM config |

### Implementation Details

#### GET `/settings`
```typescript
// Response 200
{
  user: {
    email_notifications: boolean
    slack_webhook?: string
    timezone: string
    default_project_id?: string
  }
  global: {
    default_automation_level: 'MANUAL' | 'ASSISTED' | 'SEMI_AUTO' | 'FULL_AUTO'
    mining_interval_minutes: number
    opportunity_expiry_hours: number
    max_daily_posts_per_account: number
    min_action_interval_seconds: number
  }
  llm: {
    default_model: string
    temperature: number
    max_tokens: number
    fallback_enabled: boolean
  }
}
```

---

## 10. Health & Status

| Status | Method | Endpoint | Description |
|--------|--------|----------|-------------|
| ✅ | GET | `/health` | API health check |
| ❌ | GET | `/status` | System status |
| ❌ | GET | `/status/tasks` | Background task status |

### Implementation Details

#### GET `/status` - NEW
```typescript
// Response 200
{
  status: 'healthy' | 'degraded' | 'unhealthy'
  components: {
    database: 'up' | 'down'
    redis: 'up' | 'down'
    celery: 'up' | 'down'
    reddit_api: 'up' | 'rate_limited' | 'down'
    openai_api: 'up' | 'down'
  }
  last_mining_run: string | null
  last_analytics_run: string | null
  queued_tasks: number
}
```

#### GET `/status/tasks` - NEW
```typescript
// Response 200
{
  scheduled_tasks: [
    {
      name: string
      schedule: string  // cron expression or interval
      last_run: string | null
      next_run: string
      status: 'running' | 'completed' | 'failed'
    }
  ]
  active_workers: number
  pending_tasks: {
    mining: number
    content_generation: number
    analytics: number
    account_health: number
  }
}
```

---

## Response Formats

### Success Response
```typescript
// Single resource
{
  id: string
  // ...resource fields
}

// Collection
{
  items: [...],
  total: number,
  page: number,
  per_page: number,
  pages: number
}

// Action confirmation
{
  success: true,
  message: string
}
```

### Error Response
```typescript
{
  detail: string,
  error_code?: string,
  errors?: [
    {
      field: string,
      message: string
    }
  ]
}
```

### HTTP Status Codes
| Code | Usage |
|------|-------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (successful delete) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict (duplicate) |
| 422 | Unprocessable Entity |
| 429 | Rate Limited |
| 500 | Internal Server Error |

---

## Implementation Priority

### Phase 1: Essential (Week 1)
1. ❌ Authentication endpoints (if needed)
2. 🔧 Projects - add stats to GET
3. ❌ `POST /opportunities/{id}/snooze`
4. ❌ `GET /analytics/dashboard/urgent`
5. ❌ `GET /analytics/dashboard/pipeline`

### Phase 2: Full Workflow (Week 2)
1. ❌ `GET /opportunities/{id}/reddit-comments`
2. ❌ `GET /content/{id}/variants`
3. ❌ `POST /subreddits/analyze`
4. ❌ `GET /analytics/dashboard/top-content`
5. ❌ `GET /analytics/content-styles`

### Phase 3: Polish (Week 3)
1. ❌ `GET /status` and `/status/tasks`
2. ❌ Settings endpoints
3. 🔧 Extended filters on all list endpoints
4. ❌ Account project assignment endpoints

---

## WebSocket Events (Future)

For real-time updates, consider implementing WebSocket events:

```typescript
// Events
'opportunity.discovered' - New opportunity found
'opportunity.expiring' - Opportunity window closing
'content.generated' - Content generation complete
'content.published' - Content published to Reddit
'content.performance' - Performance update
'account.health' - Account health change
'account.rate_limited' - Account rate limited
```

---

## Rate Limiting

### API Rate Limits
| Endpoint Group | Rate Limit |
|----------------|------------|
| Authentication | 5 req/min |
| Read operations | 100 req/min |
| Write operations | 30 req/min |
| Mining trigger | 1 req/5 min |
| Content generation | 10 req/min |

### Response Headers
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1609459200
```

---

## Summary

### Existing Endpoints: 35
### Endpoints Needing Extension: 5
### New Endpoints Required: 22

**Total Implementation Effort:**
- Authentication: ~1 day
- Enhanced Filters: ~0.5 day
- New CRUD endpoints: ~1 day
- Analytics endpoints: ~1.5 days
- Subreddit analysis: ~1 day
- Settings & Status: ~0.5 day

**Estimated Total: 5-6 days of backend work**
