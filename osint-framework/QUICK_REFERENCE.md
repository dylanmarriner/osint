# OSINT Framework - Quick Reference

## 🚀 Quick Start (30 seconds)

```bash
cd osint-framework
chmod +x start.sh
./start.sh
# Server running at http://localhost:8000
```

## 📋 Key Files

| File | Purpose |
|------|---------|
| `main.py` | Application entry point |
| `src/config.py` | Configuration management |
| `src/db.py` | Database models |
| `src/api/app.py` | FastAPI application |
| `.env` | Configuration (development) |
| `.env.example` | Configuration template |

## 🔧 Configuration

### Key Environment Variables

```bash
# Server
ENVIRONMENT=development              # development/testing/production
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Database
DATABASE_URL=sqlite:///./osint_framework.db
# Or PostgreSQL:
# DATABASE_URL=postgresql://user:pass@localhost/osint_db

# Frontend (CORS)
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Logging
LOG_LEVEL=DEBUG                      # DEBUG/INFO/WARNING/ERROR
```

### To Change Configuration
```bash
# Edit .env file
nano .env

# Or set environment variables
export DATABASE_URL=postgresql://...
export LOG_LEVEL=INFO
```

## 🌐 API Endpoints

### Create Investigation
```bash
POST /api/investigations
{
  "subject_identifiers": {
    "full_name": "John Doe"
  }
}
```

### List Investigations
```bash
GET /api/investigations?limit=50&offset=0
```

### Get Investigation Status
```bash
GET /api/investigations/{investigation_id}/status
```

### Get Investigation Report
```bash
GET /api/investigations/{investigation_id}/report?format=json
# format: json, markdown, or html
```

### WebSocket Real-Time Updates
```
WS ws://localhost:8000/ws/{investigation_id}
```

### Health Check
```bash
GET /api/health
```

## 🗄️ Database

### SQLite (Default)
- File: `osint_framework.db`
- No setup required
- Good for development

### PostgreSQL (Recommended for Production)
```bash
# Install
pip install psycopg2-binary

# Configure
DATABASE_URL=postgresql://user:password@localhost/osint_db

# Create database
createdb osint_db
```

### MySQL
```bash
# Install
pip install mysqlconnector-python

# Configure
DATABASE_URL=mysql://user:password@localhost/osint_db

# Create database
mysql -u root -p -e "CREATE DATABASE osint_db;"
```

## 🧪 Testing API

```bash
# Check health
curl http://localhost:8000/api/health

# List investigations
curl http://localhost:8000/api/investigations

# Create investigation
curl -X POST http://localhost:8000/api/investigations \
  -H "Content-Type: application/json" \
  -d '{
    "subject_identifiers": {
      "full_name": "Test User",
      "usernames": [],
      "emails": [],
      "phone_numbers": [],
      "known_domains": [],
      "geographic_hints": {},
      "professional_hints": {}
    }
  }'

# Get status
curl http://localhost:8000/api/investigations/{investigation_id}/status

# Get report
curl http://localhost:8000/api/investigations/{investigation_id}/report?format=json
```

## 🎨 Frontend Integration

### React Example
```bash
npx create-react-app osint-ui
cd osint-ui
npm install axios
npm start
# Server at http://localhost:3000
```

### Vue Example
```bash
npm create vite@latest osint-ui -- --template vue
cd osint-ui
npm install axios
npm run dev
# Server at http://localhost:5173
```

### API Base URL
```javascript
const API_URL = 'http://localhost:8000/api';
const WS_URL = 'ws://localhost:8000';
```

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| `PRODUCTION_GUIDE.md` | Complete deployment guide |
| `UI_SETUP.md` | Frontend integration examples |
| `CHANGES.md` | Detailed changelog |
| `IMPLEMENTATION_SUMMARY.md` | What was fixed |
| `QUICK_REFERENCE.md` | This file |

## 🐳 Docker Deployment

### Build
```bash
docker build -t osint-framework .
```

### Run
```bash
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@db:5432/osint \
  -e ENVIRONMENT=production \
  osint-framework
```

## 📊 Troubleshooting

### Port Already in Use
```bash
# Change port in .env
SERVER_PORT=8001

# Or kill process using port 8000
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

### Database Connection Error
```bash
# Check DATABASE_URL
echo $DATABASE_URL

# Test PostgreSQL connection
psql $DATABASE_URL
```

### CORS Error
```bash
# Add frontend URL to .env
CORS_ORIGINS=http://localhost:3000,http://your-domain.com
```

### WebSocket Connection Failed
```bash
# Check WS URL matches backend
WS_URL=ws://localhost:8000  # Not http://

# Check CORS origins allow WebSocket
CORS_ORIGINS must include frontend origin
```

## 🔒 Security Checklist

Before production:
- [ ] Set `DEBUG=false`
- [ ] Set `ENVIRONMENT=production`
- [ ] Use PostgreSQL (not SQLite)
- [ ] Set unique `CORS_ORIGINS`
- [ ] Enable authentication if needed
- [ ] Use HTTPS/SSL (wss:// for WebSocket)
- [ ] Set strong database password
- [ ] Disable unnecessary endpoints

## 📈 Performance Tuning

### Enable Caching
```bash
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379/0
```

### Increase Workers
```bash
SERVER_WORKERS=8
```

### Database Optimization
```bash
# Use PostgreSQL (better than SQLite)
DATABASE_URL=postgresql://...

# Add indexes manually if needed
```

## 🚢 Production Deployment

### Minimal Setup
```bash
# Create .env for production
cat > .env << EOF
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@host/osint_db
CORS_ORIGINS=https://your-domain.com
SERVER_HOST=127.0.0.1
SERVER_PORT=8000
LOG_LEVEL=WARNING
DEBUG=false
EOF

# Run with gunicorn
pip install gunicorn
gunicorn -w 4 -b 127.0.0.1:8000 src.api.app:app
```

### Behind Nginx
```nginx
upstream backend {
    server 127.0.0.1:8000;
}

server {
    listen 443 ssl;
    server_name osint.example.com;
    
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
    }
    
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 📞 Getting Help

1. Check `PRODUCTION_GUIDE.md` for deployment issues
2. See `UI_SETUP.md` for frontend problems
3. Review `.env.example` for configuration
4. Check application logs for errors
5. Test API with curl before debugging frontend

## ✅ What's Fixed

- ✅ Database persistence
- ✅ Report generation (no more mock data)
- ✅ Configuration management
- ✅ Error handling and logging
- ✅ CORS configuration
- ✅ WebSocket cleanup
- ✅ Startup/shutdown handlers

## 🎯 Common Tasks

### Change Database
```bash
# Edit .env
DATABASE_URL=postgresql://user:password@localhost/osint_db
```

### Enable Debugging
```bash
# Edit .env
DEBUG=true
LOG_LEVEL=DEBUG
```

### Add Frontend Origins
```bash
# Edit .env
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,https://my-domain.com
```

### Increase Investigation Timeout
```bash
# Edit .env
MAX_INVESTIGATION_DURATION_MINUTES=240
```

### View Logs
```bash
# Logs printed to console
# In production, redirect to file:
python main.py >> app.log 2>&1 &
tail -f app.log
```

---

**Need more details?** See the full guides:
- `PRODUCTION_GUIDE.md` - 500+ lines
- `UI_SETUP.md` - 400+ lines
- `CHANGES.md` - Complete changelog
