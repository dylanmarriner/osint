# OSINT Framework UI Setup

This guide explains how to set up and use the OSINT Framework web interface.

## Frontend Requirements

The API expects a frontend application (React, Vue, Svelte, etc.) to be served on one of the configured CORS origins.

### Default CORS Origins (Development)
```
http://localhost:3000      # React dev server (port 3000)
http://localhost:8080      # Vue dev server (port 8080)
http://localhost:5173      # Vite dev server (port 5173)
http://127.0.0.1:3000
http://127.0.0.1:8080
http://127.0.0.1:5173
```

## Minimal React Example

### 1. Create React App
```bash
npx create-react-app osint-ui
cd osint-ui
npm install axios
```

### 2. Create Investigation Service (src/services/api.js)
```javascript
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';
const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  }
});

export const createInvestigation = async (identifiers) => {
  return api.post('/investigations', {
    subject_identifiers: identifiers,
    investigation_constraints: {},
    confidence_thresholds: {}
  });
};

export const getInvestigationStatus = async (investigationId) => {
  return api.get(`/investigations/${investigationId}/status`);
};

export const getInvestigationReport = async (investigationId, format = 'json') => {
  return api.get(`/investigations/${investigationId}/report?format=${format}`);
};

export const listInvestigations = async (limit = 50, offset = 0) => {
  return api.get('/investigations', { params: { limit, offset } });
};

export const subscribeToInvestigation = (investigationId, callbacks) => {
  const ws = new WebSocket(`${WS_URL}/ws/${investigationId}`);
  
  ws.onopen = () => {
    console.log('WebSocket connected');
    if (callbacks.onConnect) callbacks.onConnect();
  };
  
  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (callbacks.onMessage) callbacks.onMessage(message);
    
    // Handle specific message types
    switch (message.type) {
      case 'status_update':
        if (callbacks.onStatusUpdate) callbacks.onStatusUpdate(message.data);
        break;
      case 'new_entity':
        if (callbacks.onNewEntity) callbacks.onNewEntity(message.data);
        break;
      case 'error':
        if (callbacks.onError) callbacks.onError(message.data);
        break;
      case 'completion':
        if (callbacks.onCompletion) callbacks.onCompletion(message.data);
        break;
      default:
        break;
    }
  };
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    if (callbacks.onError) callbacks.onError(error);
  };
  
  ws.onclose = () => {
    console.log('WebSocket disconnected');
    if (callbacks.onClose) callbacks.onClose();
  };
  
  return ws;
};

export const healthCheck = async () => {
  return api.get('/health');
};

export default api;
```

### 3. Create Investigation Component (src/components/Investigation.jsx)
```jsx
import React, { useState, useEffect } from 'react';
import {
  createInvestigation,
  getInvestigationStatus,
  getInvestigationReport,
  subscribeToInvestigation
} from '../services/api';

export default function Investigation() {
  const [investigationId, setInvestigationId] = useState(null);
  const [status, setStatus] = useState(null);
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [ws, setWs] = useState(null);

  const handleStartInvestigation = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await createInvestigation({
        full_name: fullName,
        usernames: [],
        emails: [],
        phone_numbers: [],
        known_domains: [],
        geographic_hints: {},
        professional_hints: {}
      });
      
      const newInvestigationId = response.data.investigation_id;
      setInvestigationId(newInvestigationId);
      
      // Subscribe to investigation updates
      const newWs = subscribeToInvestigation(newInvestigationId, {
        onStatusUpdate: (data) => setStatus(data),
        onCompletion: (data) => {
          console.log('Investigation completed:', data);
          setStatus(data);
        },
        onError: (error) => console.error('Investigation error:', error)
      });
      
      setWs(newWs);
    } catch (error) {
      console.error('Failed to create investigation:', error);
      alert('Failed to start investigation');
    } finally {
      setLoading(false);
    }
  };

  const handleGetReport = async () => {
    try {
      const response = await getInvestigationReport(investigationId, 'json');
      console.log('Report:', response.data);
      // Display report in your UI
    } catch (error) {
      console.error('Failed to get report:', error);
      alert('Failed to get report');
    }
  };

  useEffect(() => {
    return () => {
      if (ws) ws.close();
    };
  }, [ws]);

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>OSINT Investigation</h1>
      
      {!investigationId ? (
        <form onSubmit={handleStartInvestigation}>
          <div style={{ marginBottom: '10px' }}>
            <label>Full Name:</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              style={{ width: '100%', padding: '5px' }}
            />
          </div>
          <button type="submit" disabled={loading}>
            {loading ? 'Starting...' : 'Start Investigation'}
          </button>
        </form>
      ) : (
        <div>
          <p>Investigation ID: {investigationId}</p>
          {status && (
            <div style={{ border: '1px solid #ccc', padding: '10px', marginTop: '10px' }}>
              <h3>Status: {status.status}</h3>
              <p>Progress: {status.progress_percentage}%</p>
              <p>Current Stage: {status.current_stage}</p>
              <p>Entities Found: {status.entities_found}</p>
              <p>Queries Executed: {status.queries_executed}</p>
              {status.errors.length > 0 && (
                <div style={{ color: 'red' }}>
                  <p>Errors:</p>
                  <ul>
                    {status.errors.map((error, i) => <li key={i}>{error}</li>)}
                  </ul>
                </div>
              )}
            </div>
          )}
          {status?.status === 'completed' && (
            <button onClick={handleGetReport} style={{ marginTop: '10px' }}>
              Download Report
            </button>
          )}
        </div>
      )}
    </div>
  );
}
```

### 4. Update App.jsx
```jsx
import Investigation from './components/Investigation';

function App() {
  return (
    <div className="App">
      <Investigation />
    </div>
  );
}

export default App;
```

### 5. Configure Environment (.env)
```
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_WS_URL=ws://localhost:8000
```

### 6. Run the Frontend
```bash
npm start
```

Your React app should open at http://localhost:3000

## Minimal Vue Example

### 1. Create Vue App
```bash
npm create vite@latest osint-ui -- --template vue
cd osint-ui
npm install axios
npm run dev
```

### 2. Create API Module (src/api.js)
```javascript
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

const api = axios.create({ baseURL: API_URL });

export default {
  async createInvestigation(identifiers) {
    return api.post('/investigations', {
      subject_identifiers: identifiers,
      investigation_constraints: {},
      confidence_thresholds: {}
    });
  },

  subscribeToInvestigation(investigationId) {
    return new WebSocket(`${WS_URL}/ws/${investigationId}`);
  },

  async getInvestigationReport(investigationId, format = 'json') {
    return api.get(`/investigations/${investigationId}/report?format=${format}`);
  }
};
```

### 3. Create Investigation Component (src/components/Investigation.vue)
```vue
<template>
  <div class="investigation">
    <h1>OSINT Investigation</h1>
    
    <form @submit.prevent="startInvestigation" v-if="!investigationId">
      <div>
        <label>Full Name:</label>
        <input v-model="fullName" required />
      </div>
      <button :disabled="loading">
        {{ loading ? 'Starting...' : 'Start Investigation' }}
      </button>
    </form>

    <div v-else>
      <p>Investigation ID: {{ investigationId }}</p>
      <div v-if="status" class="status">
        <h3>Status: {{ status.status }}</h3>
        <p>Progress: {{ status.progress_percentage }}%</p>
        <p>Current Stage: {{ status.current_stage }}</p>
        <p>Entities Found: {{ status.entities_found }}</p>
        <button 
          v-if="status.status === 'completed'" 
          @click="getReport"
        >
          Download Report
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue';
import api from '../api';

export default {
  setup() {
    const fullName = ref('');
    const investigationId = ref(null);
    const status = ref(null);
    const loading = ref(false);
    const ws = ref(null);

    const startInvestigation = async () => {
      loading.value = true;
      try {
        const response = await api.createInvestigation({
          full_name: fullName.value,
          usernames: [],
          emails: [],
          phone_numbers: [],
          known_domains: [],
          geographic_hints: {},
          professional_hints: {}
        });

        investigationId.value = response.data.investigation_id;

        // Subscribe to updates
        ws.value = api.subscribeToInvestigation(investigationId.value);
        ws.value.onmessage = (event) => {
          const message = JSON.parse(event.data);
          if (message.type === 'status_update') {
            status.value = message.data;
          }
        };
      } catch (error) {
        alert('Failed to start investigation: ' + error.message);
      } finally {
        loading.value = false;
      }
    };

    const getReport = async () => {
      try {
        const response = await api.getInvestigationReport(investigationId.value);
        console.log('Report:', response.data);
      } catch (error) {
        alert('Failed to get report');
      }
    };

    return {
      fullName,
      investigationId,
      status,
      loading,
      startInvestigation,
      getReport
    };
  }
};
</script>

<style scoped>
.investigation {
  padding: 20px;
  font-family: Arial, sans-serif;
}

.status {
  border: 1px solid #ccc;
  padding: 10px;
  margin-top: 10px;
}

input, button {
  padding: 5px;
  margin: 5px 0;
}
</style>
```

### 4. Configure Environment (.env.local)
```
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000
```

## API Integration Checklist

- [x] Backend API running on http://localhost:8000
- [x] Database initialized and tables created
- [x] CORS origins configured in .env
- [x] Frontend server running on a configured CORS origin
- [x] API endpoints working (test with curl)
- [x] WebSocket connections established
- [x] Investigation creation working
- [x] Real-time status updates working
- [x] Report retrieval working

## Testing the UI

### 1. Start Backend
```bash
cd osint-framework
python main.py
```

### 2. Test API Directly
```bash
# Health check
curl http://localhost:8000/api/health

# List investigations
curl http://localhost:8000/api/investigations

# Create investigation
curl -X POST http://localhost:8000/api/investigations \
  -H "Content-Type: application/json" \
  -d '{
    "subject_identifiers": {
      "full_name": "John Doe",
      "usernames": [],
      "emails": [],
      "phone_numbers": [],
      "known_domains": [],
      "geographic_hints": {},
      "professional_hints": {}
    }
  }'
```

### 3. Start Frontend
```bash
cd osint-ui
npm run dev
```

### 4. Test in Browser
- Navigate to http://localhost:3000 (React) or http://localhost:5173 (Vite)
- Fill in the form with a name
- Click "Start Investigation"
- Watch real-time updates
- Download report when complete

## Troubleshooting

### CORS Error
**Error**: `Access to XMLHttpRequest blocked by CORS policy`

**Solution**: Add your frontend URL to `CORS_ORIGINS` in `.env`:
```
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,...
```

Then restart the backend.

### WebSocket Connection Failed
**Error**: `WebSocket connection failed`

**Solution**:
1. Verify `WS_URL` matches your backend URL
2. Check WebSocket path: `/ws/{investigation_id}`
3. Ensure backend is running
4. Check firewall settings

### API Not Responding
**Error**: `Cannot GET /api/...`

**Solution**:
1. Backend running? `curl http://localhost:8000/api/health`
2. Correct API_URL in frontend? Should be `http://localhost:8000/api`
3. No typos in endpoint paths

## Production Deployment

When deploying to production:

1. **Update CORS origins** in `.env`:
   ```
   CORS_ORIGINS=https://yourfrontend.com
   ```

2. **Use HTTPS** for WebSocket connections:
   ```javascript
   const WS_URL = 'wss://yourdomain.com'; // Instead of ws://
   ```

3. **Set environment variables**:
   ```javascript
   VITE_API_URL=https://api.yourdomain.com
   VITE_WS_URL=wss://api.yourdomain.com
   ```

4. **Enable authentication** in backend `.env`:
   ```
   ENABLE_AUTH=true
   ```

5. **Build and deploy frontend**:
   ```bash
   npm run build
   # Deploy dist/ folder to your hosting
   ```
