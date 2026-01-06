# Reddit Content Platform

A production-ready Reddit-first Organic Advertising Platform that discovers high-value Reddit opportunities, generates authentic content, and learns from performance.

## Features

- **Opportunity Mining**: Automatically discovers rising posts in target subreddits using velocity-based scoring
- **Smart Content Generation**: LLM-powered content creation with multiple style variants (OpenAI + Anthropic)
- **Quality Gates**: Multi-layer content validation including spam detection, promotional language detection, and authenticity scoring
- **Multi-Account Management**: OAuth2-based Reddit account management with intelligent account selection
- **Performance Analytics**: Track engagement, detect removals, and learn from outcomes
- **Adaptive Learning**: Thompson Sampling-based feature learning for continuous improvement
- **Celery Task Queue**: Background processing for mining, generation, analytics, and account health checks

## Architecture

```
reddit-content-platform/
├── app/
│   ├── api/endpoints/     # FastAPI route handlers
│   ├── core/              # Configuration, Celery, security
│   ├── db/                # Database setup, migrations
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic services
│   ├── tasks/             # Celery background tasks
│   └── utils/             # Utility functions
├── alembic/               # Database migrations
├── tests/                 # Test suite
├── docker-compose.yml     # Docker services
└── Dockerfile
```

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional, recommended)

## Quick Start

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd reddit-content-platform
```

2. Create environment file:
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. Start all services:
```bash
docker-compose up -d
```

4. Run database migrations:
```bash
docker-compose exec app alembic upgrade head
```

5. Access the API:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Flower (Celery monitoring): http://localhost:5555

### Manual Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

2. Set up PostgreSQL and Redis:
```bash
# Install and start PostgreSQL
# Install and start Redis
```

3. Create environment file:
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. Run migrations:
```bash
alembic upgrade head
```

5. Start the application:
```bash
# Terminal 1: FastAPI server
uvicorn app.main:app --reload

# Terminal 2: Celery worker
celery -A app.core.celery_app worker -l info -Q default,opportunity-mining,content-generation,analytics,account-health

# Terminal 3: Celery beat (scheduler)
celery -A app.core.celery_app beat -l info
```

## Configuration

### Required Environment Variables

```bash
# Database
POSTGRES_USER=reddit_platform
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=reddit_platform

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Reddit OAuth
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_REDIRECT_URI=http://localhost:8000/api/v1/reddit/auth/callback
REDDIT_USER_AGENT=reddit-content-platform:v1.0.0

# LLM APIs
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...  # Optional fallback

# Security
SECRET_KEY=your_jwt_secret_key
ENCRYPTION_KEY=your_32_byte_fernet_key  # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Reddit App Setup

1. Go to https://www.reddit.com/prefs/apps
2. Create a new application:
   - Type: Web app
   - Redirect URI: `http://localhost:8000/api/v1/reddit/auth/callback`
3. Copy the client ID and secret to your `.env` file

## API Endpoints

### Projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects` - List projects
- `GET /api/v1/projects/{id}` - Get project
- `PUT /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project
- `POST /api/v1/projects/{id}/subreddits` - Add subreddit config

### Opportunities
- `GET /api/v1/opportunities` - List opportunities
- `GET /api/v1/opportunities/{id}` - Get opportunity
- `POST /api/v1/opportunities/{id}/approve` - Approve opportunity
- `POST /api/v1/opportunities/{id}/reject` - Reject opportunity
- `POST /api/v1/opportunities/{id}/generate-content` - Generate content
- `POST /api/v1/opportunities/mine` - Trigger manual mining

### Content
- `GET /api/v1/content` - List content
- `GET /api/v1/content/{id}` - Get content
- `PUT /api/v1/content/{id}` - Update content
- `POST /api/v1/content/{id}/regenerate` - Regenerate content
- `POST /api/v1/content/{id}/approve` - Approve content
- `POST /api/v1/content/{id}/reject` - Reject content
- `POST /api/v1/content/{id}/publish` - Publish to Reddit
- `GET /api/v1/content/{id}/performance` - Get performance metrics

### Reddit Accounts
- `GET /api/v1/reddit/auth/url` - Get OAuth URL
- `GET /api/v1/reddit/auth/callback` - OAuth callback
- `GET /api/v1/accounts` - List accounts
- `GET /api/v1/accounts/{id}` - Get account
- `DELETE /api/v1/accounts/{id}` - Deactivate account
- `POST /api/v1/accounts/{id}/health-check` - Check account health

### Analytics
- `GET /api/v1/analytics/projects/{id}/summary` - Project analytics
- `GET /api/v1/analytics/projects/{id}/performance` - Performance time series
- `GET /api/v1/analytics/subreddits/{name}/insights` - Subreddit insights
- `GET /api/v1/analytics/learning-features` - Learning features
- `GET /api/v1/analytics/dashboard` - Dashboard summary

## Key Algorithms

### Rising Post Velocity
```python
velocity = (score / age_hours) * 0.7 + (comments / age_hours) * 0.3 * 10
```

Velocity thresholds by subreddit size:
- <50k subscribers: velocity > 5
- 50k-500k: velocity > 15
- 500k-2M: velocity > 50
- >2M: velocity > 200

### Urgency Classification
- **URGENT**: velocity > threshold*2 AND age < 1 hour (act within 30 min)
- **HIGH**: velocity > threshold AND age < 2 hours (act within 2 hours)
- **MEDIUM**: velocity > threshold*0.5 AND age < 4 hours
- **LOW**: everything else

### Account Selection Score
```python
score = 100.0
score += min(karma / 1000, 20)        # up to +20
score += min(age_days / 30, 10)       # up to +10
score += 15 if has_subreddit_history else 0
score += 10 if removal_rate < 0.05 else 0
score -= 20 if removal_rate > 0.20 else 0
score *= health_score
```

## Background Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `scheduled_mining` | Every 15 min | Mine opportunities for active projects |
| `collect_all_analytics` | Every 30 min | Collect metrics for published content |
| `check_all_accounts_health` | Every hour | Verify OAuth tokens and update karma |
| `reset_daily_limits` | Daily midnight | Reset account daily action counters |
| `update_learning_features` | Daily 3 AM | Update ML features from performance |

## Automation Levels

1. **Manual**: Human reviews all decisions
2. **Assisted**: Auto-discovery, human approves
3. **Semi-Auto**: Auto-discovery + generation, human approves publish
4. **Full Auto**: Complete automation (for URGENT items only)

## Development

### Running Tests
```bash
pytest tests/ -v
```

### Code Quality
```bash
# Format code
black app/ tests/
isort app/ tests/

# Type checking
mypy app/

# Linting
ruff app/ tests/
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Monitoring

- **Flower**: Celery task monitoring at http://localhost:5555
- **Health Endpoint**: `GET /health` for application health
- **Structured Logging**: JSON logs for all operations

## Success Metrics

Target benchmarks:
- ML virality scoring: AUC > 0.80
- Content removal rate: < 15%
- URGENT opportunities: > 60% published within 30 min
- HIGH opportunities: > 80% published within 2 hours

## License

MIT License - see LICENSE file for details.
