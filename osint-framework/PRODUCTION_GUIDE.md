# OSINT Framework - Production Deployment Guide

This guide covers the production-grade changes made to the OSINT Framework and how to deploy it successfully.

## What's Been Fixed

### Critical Issues Resolved

1. **Data Persistence**
   - ✅ Implemented SQLAlchemy ORM for database abstraction
   - ✅ Added SQLite support (default) with PostgreSQL/MySQL compatibility
   - ✅ All investigations and reports now persist to database
   - ✅ Data survives server restarts

2. **Report Generation**
   - ✅ Replaced mock/sample report generation with real database retrieval
   - ✅ Reports are stored after investigation completion
   - ✅ Multiple report formats supported (JSON, Markdown, HTML)

3. **Error Handling**
   - ✅ Replaced all bare `except: pass` blocks with proper logging
   - ✅ Better debugging and error visibility
   - ✅ Structured logging throughout

4. **Configuration Management**
   - ✅ Environment-based configuration system
   - ✅ No more hardcoded values
   - ✅ Support for development, testing, and production environments
   - ✅ `.env` file support via python-dotenv

5. **API Improvements**
   - ✅ Added `/api/investigations` endpoint for listing all investigations
   - ✅ Improved `/api/investigations/{id}/status` with database fallback
   - ✅ Fixed `/api/investigations/{id}/report` to retrieve real reports
   - ✅ Added database dependency injection to endpoints

6. **Startup/Shutdown**
   - ✅ Database initialization on startup
   - ✅ Graceful resource cleanup on shutdown
   - ✅ WebSocket connection management

## Architecture Changes

### Database Layer
```
src/db.py (NEW)
├── Investigation (ORM model)
├── InvestigationReport (ORM model)
├── SearchQueryCache (ORM model)
├── EntityCache (ORM model)
└── Helper functions for CRUD operations
```

### Configuration Layer
```
src/config.py (NEW)
├── Config (base class with defaults)
├── DevelopmentConfig
├── TestingConfig
├── ProductionConfig
└── get_config() factory function
```

### API Updates
```
src/api/app.py (UPDATED)
├── Database integration
├── Environment-based CORS configuration
├── Proper exception handling in report endpoints
├── New /api/investigations listing endpoint
├── Startup/shutdown event handlers
└── Dynamic host/port configuration
```

### Error Handling Improvements
```
src/core/pipeline/parse.py (UPDATED)
├── Logged exception handlers instead of bare pass
├── Better debugging information
└── Structured error messages
```

## Setup Instructions

### 1. Prerequisites
- Python 3.8+
- pip or pip3
- Virtual environment (recommended)

### 2. Clone and Setup
```bash
cd osint-framework
chmod +x start.sh
./start.sh
```

Or manually:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env for your environment
nano .env
```

Key configuration options:
- `ENVIRONMENT`: development, testing, production
- `DATABASE_URL`: Database connection string
- `CORS_ORIGINS`: Allowed frontend origins
- `SERVER_HOST`: Server binding address
- `SERVER_PORT`: Server port

### 4. Run the Application
```bash
python main.py
```

Or with uvicorn directly:
```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

## Database Setup

### SQLite (Development - Default)
No additional setup required. Database file created at `./osint_framework.db`

### PostgreSQL (Production Recommended)
```bash
# Install postgres driver
pip install psycopg2-binary

# Update .env
DATABASE_URL=postgresql://user:password@localhost/osint_db
ENVIRONMENT=production

# Create database
createdb osint_db
```

### MySQL
```bash
# Install mysql driver
pip install mysqlconnector-python

# Update .env
DATABASE_URL=mysql://user:password@localhost/osint_db
ENVIRONMENT=production

# Create database
mysql -u user -p -e "CREATE DATABASE osint_db;"
```

## API Endpoints

### Investigations
```
POST /api/investigations
- Create a new investigation

GET /api/investigations
- List all investigations
- Query params: limit (50), offset (0)

GET /api/investigations/{investigation_id}/status
- Get investigation status
- Returns status from active cache or database

GET /api/investigations/{investigation_id}/report
- Get completed investigation report
- Query params: format (json, markdown, html)
- Returns actual report from database

DELETE /api/investigations/{investigation_id}
- Delete investigation and associated reports
```

### WebSocket
```
WS /ws/{investigation_id}
- Real-time investigation progress updates
- Authenticated connection management
```

### System
```
GET /api/health
- Health check endpoint
- Component status information
```

## Production Deployment

### Security Checklist
- [ ] Set `DEBUG=false` in .env
- [ ] Set `ENVIRONMENT=production`
- [ ] Use PostgreSQL or MySQL instead of SQLite
- [ ] Set `CORS_ORIGINS` to your frontend domain only
- [ ] Enable authentication (`ENABLE_AUTH=true`)
- [ ] Use HTTPS/SSL in production
- [ ] Set strong database passwords
- [ ] Use environment variables for secrets (never commit .env)
- [ ] Enable rate limiting (`RATE_LIMIT_ENABLED=true`)

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV ENVIRONMENT=production
ENV DEBUG=false

CMD ["python", "main.py"]
```

### Docker Compose
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:password@db:5432/osint_db
      REDIS_URL: redis://cache:6379/0
      ENVIRONMENT: production
    depends_on:
      - db
      - cache

  db:
    image: postgres:13
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: osint_db
    volumes:
      - postgres_data:/var/lib/postgresql/data

  cache:
    image: redis:7

volumes:
  postgres_data:
```

### Reverse Proxy (Nginx)
```nginx
upstream osint_backend {
    server 127.0.0.1:8000;
}

server {
    listen 443 ssl http2;
    server_name osint.example.com;

    ssl_certificate /etc/letsencrypt/live/osint.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/osint.example.com/privkey.pem;

    location / {
        proxy_pass http://osint_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://osint_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Monitoring

### Health Endpoint
```bash
curl http://localhost:8000/api/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00.000000",
  "version": "1.0.0",
  "components": {
    "discovery_engine": "initialized",
    "fetch_manager": "ok",
    "parse_engine": "ok",
    "normalization_engine": "ok",
    "entity_resolver": "ok",
    "report_generator": "ok",
    "websocket_connections": {
      "total_connections": 0,
      "investigation_subscriptions": {}
    }
  }
}
```

### Logging
- Check console output for structured logs
- All errors are now logged with context
- Set `LOG_LEVEL=DEBUG` for development debugging

## Troubleshooting

### Database Connection Failed
```
ERROR: Failed to initialize database
```
- Check `DATABASE_URL` is correct
- Verify database exists and user has permissions
- Check firewall/network connectivity

### Port Already in Use
```
ERROR: Address already in use
```
```bash
# Find process using port 8000
lsof -i :8000

# Change port in .env
SERVER_PORT=8001
```

### WebSocket Connection Failed
- Check frontend CORS origins in .env
- Verify WebSocket path is `/ws/{investigation_id}`
- Check browser console for connection errors

### Reports Not Saving
- Check `REPORT_STORAGE_PATH` directory exists and is writable
- Verify database connectivity
- Check disk space availability

## Performance Tuning

### Database Optimization
- Use PostgreSQL for production (better concurrency)
- Enable connection pooling
- Create database indexes for frequent queries
- Regular VACUUM/ANALYZE on PostgreSQL

### Caching
- Enable Redis for session caching
- Cache report exports
- Implement query result caching

### API Rate Limiting
- Adjust `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_PERIOD`
- Consider per-IP rate limiting behind reverse proxy
- Monitor rate limit violations

### Worker Processes
```bash
uvicorn src.api.app:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

## Migration from Old Version

If upgrading from pre-production version:

1. Backup old data if any
2. Update to new version
3. Run database initialization automatically on startup
4. Old in-memory data is NOT migrated (fresh start)
5. All new investigations use database

## Version History

### v1.0.0 (Production-Ready)
- ✅ Full database persistence
- ✅ Configuration management
- ✅ Proper error handling
- ✅ Security hardening
- ✅ Docker support

## Support and Contributing

For issues, improvements, or feature requests, please open an issue or submit a pull request.

## License

See LICENSE file for details.
