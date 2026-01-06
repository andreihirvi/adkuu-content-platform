// Core entity types

export interface Project {
  id: number;
  name: string;
  description: string | null;
  product_url: string | null;
  keywords: string[];
  tone_guidelines: string | null;
  target_subreddits: string[];
  is_active: boolean;
  daily_comment_limit: number;
  created_at: string;
  updated_at: string;
}

export interface RedditAccount {
  id: number;
  username: string;
  display_name: string;
  project_id: number | null;
  status: 'active' | 'inactive' | 'rate_limited' | 'oauth_expired' | 'suspended';
  health_score: number;
  karma_total: number;
  karma_comment: number;
  karma_post: number;
  account_age_days: number | null;
  daily_actions_count: number;
  last_action_at: string | null;
  last_health_check_at: string | null;
  total_posts_made: number;
  total_posts_removed: number;
  removal_rate: number;
  created_at: string;
  updated_at: string;
}

export type OpportunityStatus = 'new' | 'queued' | 'in_progress' | 'completed' | 'skipped' | 'expired';
export type UrgencyLevel = 'critical' | 'high' | 'medium' | 'low';

export interface Opportunity {
  id: number;
  project_id: number;
  reddit_post_id: string;
  subreddit: string;
  post_title: string;
  post_url: string;
  post_author: string;
  post_score: number;
  post_num_comments: number;
  post_created_utc: string;
  relevance_score: number;
  urgency_level: UrgencyLevel;
  status: OpportunityStatus;
  discovered_at: string;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
  // Relations
  project?: Project;
  generated_contents?: GeneratedContent[];
}

export type ContentStatus = 'draft' | 'pending_review' | 'approved' | 'rejected' | 'published' | 'failed';
export type ContentType = 'comment' | 'post';

export interface GeneratedContent {
  id: number;
  opportunity_id: number;
  content_type: ContentType;
  content_text: string;
  generation_model: string;
  quality_score: number | null;
  authenticity_score: number | null;
  relevance_score: number | null;
  status: ContentStatus;
  rejection_reason: string | null;
  published_at: string | null;
  reddit_comment_id: string | null;
  created_at: string;
  updated_at: string;
  // Relations
  opportunity?: Opportunity;
  performance?: ContentPerformance;
}

export interface ContentPerformance {
  id: number;
  content_id: number;
  upvotes: number;
  downvotes: number;
  score: number;
  num_replies: number;
  is_top_comment: boolean;
  hours_in_top_10: number;
  engagement_rate: number | null;
  last_updated_at: string;
  created_at: string;
}

export interface SubredditConfig {
  id: number;
  project_id: number;
  subreddit_name: string;
  is_enabled: boolean;
  priority: number;
  min_post_score: number;
  min_relevance_score: number;
  posting_frequency: string | null;
  custom_guidelines: string | null;
  created_at: string;
  updated_at: string;
}

// Dashboard stats
export interface DashboardStats {
  opportunities: {
    total: number;
    by_urgency: Record<UrgencyLevel, number>;
    new_today: number;
  };
  content: {
    pending_review: number;
    published_today: number;
    total_published: number;
  };
  performance: {
    total_upvotes: number;
    avg_engagement_rate: number;
    top_comments_count: number;
  };
  accounts: {
    total: number;
    healthy: number;
    in_cooldown: number;
  };
}

// API response types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface ApiError {
  detail: string;
  status_code?: number;
}

// Auth types
export type UserRole = 'admin' | 'user';

export interface User {
  id: number;
  email: string;
  name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Session {
  user: User;
  token: string;
}

// Filter types
export interface OpportunityFilters {
  status?: OpportunityStatus[];
  urgency_level?: UrgencyLevel[];
  project_id?: number;
  subreddit?: string;
  min_score?: number;
}

export interface ContentFilters {
  status?: ContentStatus[];
  project_id?: number;
  opportunity_id?: number;
}
