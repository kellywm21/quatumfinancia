# Deploying to Render

This guide shows how to deploy the Advancia Payledger API to Render.

## Prerequisites

1. A Render account (create at https://render.com)
2. GitHub repository access
3. Environment variables prepared

## Setup Steps

### 1. Create a Web Service on Render

- Log in to Render Dashboard
- Click **New +** > **Web Service**
- Connect your GitHub repository
- Select the `quatumfinancia` repository
- Configure the build and start commands:
  - **Build Command**: `pip install -r requirements.txt`
  - **Start Command**: `python -m src.main`

### 2. Set Environment Variables

In the Render dashboard, under **Environment**, add:

```
DATABASE_URL=postgresql://user:password@hostname:5432/database
JWT_SECRET_KEY=your-secret-key-here
USE_MOCK_LITHIC=true
EMAIL_TEST_MODE=false
ALLOW_AUTO_VERIFY=false
LITHIC_API_KEY=your-lithic-key-or-empty
```

For database, use Render's PostgreSQL service or provide your own database URL.

### 3. Deploy

Render automatically builds and deploys on every `git push` to `main`. Monitor the build logs in the Render dashboard.

## Database Setup

Option A: Use Render's PostgreSQL addon
- Click **Add PostgreSQL** in the Render dashboard
- Render will automatically inject `DATABASE_URL`

Option B: Use external database
- Provide a full PostgreSQL connection string in `DATABASE_URL`

## Monitoring

- View logs in Render dashboard under **Logs**
- Healthcheck endpoint: `https://your-app.onrender.com/health`
- For issues, review the deployment logs and error output

## Scaling

Render provides auto-scaling based on CPU/memory usage. For high-traffic applications, consider upgrading the instance type in Render's plan settings.
