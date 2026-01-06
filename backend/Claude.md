# Reddit Content Platform - Development Guide

## Overview

Reddit-first organic content advertising platform. Automatically discovers advertising opportunities on Reddit, generates authentic content, and tracks performance.

## Documentation

- **Backoffice Spec:** `docs/BACKOFFICE_SPEC.md` - Complete frontend specification
- **API Endpoints:** `docs/API_ENDPOINTS_SPEC.md` - API requirements and extensions
- **TO-BE Vision:** See `/Users/andrew/Projects/Advertising Platform/docs/TO-BE-PLATFORM-BRAINSTORM.md`

## Tech Stack

### Backend (This Repo)
- **Framework:** FastAPI (Python 3.11+)
- **Database:** PostgreSQL 15+
- **Queue:** Celery + Redis
- **ORM:** SQLAlchemy 2.0

### Frontend (To Be Built)
- **Framework:** Next.js 14
- **UI Library:** shadcn/ui (Radix UI + Tailwind CSS)
- **State:** Zustand
- **Deployment:** Vercel

## Project Structure

```
app/
├── api/endpoints/     # API routes (projects, opportunities, content, accounts, analytics)
├── models/            # SQLAlchemy models (7 core models)
├── services/          # Business logic (miner, generator, publisher, quality gates)
├── tasks/             # Celery background tasks
├── core/              # Config, Celery app
└── db/                # Database session
```

## Core Models

1. **Project** - Product/service to promote
2. **RedditAccount** - OAuth-connected Reddit accounts
3. **Opportunity** - Discovered Reddit posts
4. **GeneratedContent** - LLM-generated responses
5. **ContentPerformance** - Performance metrics
6. **SubredditConfig** - Per-subreddit settings
7. **LearningFeature** - ML optimization data

## Key Services

- `OpportunityMiner` - Discovers rising Reddit posts
- `ContentGenerator` - LLM content generation (OpenAI/Anthropic)
- `QualityGates` - Content validation
- `RedditPublisher` - Publishes to Reddit
- `RedditAnalyticsService` - Collects performance metrics

## Development

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload

# Start Celery worker
celery -A app.core.celery_app worker --loglevel=info

# Start Celery beat (scheduler)
celery -A app.core.celery_app beat --loglevel=info
```

### Environment Variables
```
DATABASE_URL=postgresql://user:pass@localhost:5432/reddit_platform
REDIS_URL=redis://localhost:6379/0
REDDIT_CLIENT_ID=xxx
REDDIT_CLIENT_SECRET=xxx
REDDIT_REDIRECT_URI=http://localhost:8000/api/v1/reddit/auth/callback
OPENAI_API_KEY=xxx
ANTHROPIC_API_KEY=xxx
SECRET_KEY=xxx
ENCRYPTION_KEY=xxx
```

## API Documentation

- Swagger UI: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`

## Background Tasks (Celery Beat)

| Task | Schedule | Purpose |
|------|----------|---------|
| `mine_opportunities` | Every 15 min | Discover new opportunities |
| `collect_analytics` | Every 30 min | Collect content performance |
| `check_account_health` | Every hour | Verify Reddit accounts |
| `update_learning_features` | Daily 3 AM | Update ML features |
| `expire_old_opportunities` | Daily 4 AM | Mark old opportunities expired |

## Workflow

```
1. Project Setup
   └─ Create Project → Add Subreddits → Connect Reddit Accounts

2. Opportunity Discovery (automated)
   └─ Mine → Score → Classify Urgency → Queue

3. Content Generation
   └─ Select Opportunity → Generate → Quality Gates → Human Review

4. Publishing
   └─ Approve → Select Account → Publish → Track

5. Learning
   └─ Collect Metrics → Update Features → Improve Scoring
```

## Related Projects

- **Advertising Platform:** `/Users/andrew/Projects/Advertising Platform`
- **adkuu-backoffice:** `/Users/andrew/Projects/Adkuu/adkuu-backoffice` (Reference frontend)
- **tracking-service:** `/Users/andrew/Projects/Adkuu/tracking-service` (Link tracking)
