# Frontend Migration to React/Next.js

## Overview

The VTS Report Tool frontend has been successfully migrated from Streamlit (Python) to a modern React application using:

- **React 19** with TypeScript
- **Vite** as the build tool
- **React Router v7** for routing
- **Tailwind CSS v4** for styling
- **Lucide React** for icons
- **Axios** for API calls
- **JWT** for authentication

## Project Structure

```
frontend/
├── public/
│   └── Kenhalogo.png          # Logo
├── src/
│   ├── components/
│   │   ├── Header.tsx         # Top header with user info
│   │   ├── Layout.tsx         # Main layout wrapper
│   │   ├── ProtectedRoute.tsx # Auth guard
│   │   └── Sidebar.tsx        # Navigation sidebar
│   ├── contexts/
│   │   └── AuthContext.tsx    # Authentication state
│   ├── lib/
│   │   └── api.ts             # Axios instance
│   ├── pages/
│   │   ├── AccidentAnalysis.tsx
│   │   ├── BreaksPickups.tsx
│   │   ├── Dashboard.tsx
│   │   ├── GPSTracking.tsx
│   │   ├── IdleAnalyzer.tsx
│   │   ├── IncidentReport.tsx
│   │   ├── Login.tsx
│   │   └── ReportSearch.tsx
│   ├── App.tsx
│   ├── index.css              # Global styles + Tailwind
│   ├── main.tsx
│   └── vite-env.d.ts
├── .env
├── .env.example
├── index.html
├── package.json
├── README.md
├── tsconfig.json
├── tsconfig.node.json
└── vite.config.ts
```

## Backend Changes

### New Files

1. **backend/auth.py** - JWT authentication utilities
   - Password hashing with bcrypt
   - Token generation and validation
   - User authentication

2. **backend/api_routes.py** - REST API endpoints
   - `/api/auth/login` - User login
   - `/api/auth/me` - Get current user
   - `/api/incidents` - CRUD for incidents
   - `/api/dashboard/stats` - Dashboard statistics

3. **backend/requirements.txt** - Updated dependencies
   - Added: python-jose, passlib, sqlalchemy, psycopg2-binary

### Modified Files

1. **backend/main.py**
   - Added CORS middleware
   - Included API routes

## Running the Application

### Option 1: Using Batch Scripts (Windows)

**Terminal 1 - Backend:**
```bash
start-backend.bat
```

**Terminal 2 - Frontend:**
```bash
start-frontend.bat
```

### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
.venv\Scripts\activate
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Access the Application

- **Frontend**: http://localhost:3000 (or http://localhost:5173 if Vite uses that port)
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Default Login Credentials

Use the same credentials as the Streamlit app:

| Contractor | Username | Password | Role |
|------------|----------|----------|------|
| RE Office | admin | Pass@12345 | re_admin |
| Wizpro | wizpro_admin | Pass@12345 | admin |
| Paschal | paschal_admin | Pass@12345 | admin |

## Features Implemented

### ✅ Completed

1. **Authentication**
   - Login page with contractor selection
   - JWT token-based auth
   - Protected routes
   - Auto-redirect on token expiry

2. **Layout & Navigation**
   - Responsive sidebar navigation
   - Header with user info
   - Role-based menu items

3. **Dashboard**
   - Statistics cards
   - Recent activity section

4. **Incident Report**
   - Form with all required fields
   - Image upload placeholder

5. **API Integration**
   - Axios instance with interceptors
   - Automatic token injection
   - Error handling

### 🚧 To Be Implemented

1. **Idle Time Analyzer**
   - Excel file upload
   - Data parsing and display
   - Save to database

2. **Breaks & Pickups**
   - CRUD interface
   - Date/time pickers

3. **Report Search**
   - Filters
   - Data table
   - Export functionality

4. **GPS Tracking**
   - Map integration (Leaflet/Mapbox)
   - Vehicle markers
   - Real-time updates

5. **Accident Analysis**
   - File upload
   - Data visualization

6. **Image Upload**
   - Multi-file upload
   - Preview
   - Compression

## Environment Variables

### Frontend (.env)
```
VITE_API_URL=http://localhost:8000/api
```

### Backend
```
DATABASE_URL=postgresql://user:password@host:port/database  # Optional, uses SQLite if not set
SECRET_KEY=your-secret-key-change-in-production
API_TOKEN=replace_with_device_token
S3_BUCKET=your-s3-bucket
AWS_REGION=us-east-1
```

## Deployment

### Frontend (Vercel)

1. Push to GitHub
2. Import in Vercel
3. Set environment variables:
   - `VITE_API_URL`: Your production API URL
4. Deploy

### Backend (Railway/Render)

1. Push to GitHub
2. Create new service
3. Set environment variables
4. Deploy

## Migration Notes

### What Changed

1. **UI Framework**: Streamlit → React
2. **Styling**: Streamlit components → Tailwind CSS
3. **Routing**: Streamlit pages → React Router
4. **State**: Streamlit session_state → React Context
5. **API**: Direct DB calls → REST API endpoints
6. **Auth**: Session-based → JWT tokens

### What Stayed the Same

1. Database schema (no changes)
2. Business logic
3. User roles and permissions
4. Feature set

### Benefits

1. **Performance**: Faster page loads, no full page reloads
2. **User Experience**: Modern, responsive UI
3. **Scalability**: Separate frontend/backend
4. **Deployment**: Easy to deploy on modern platforms
5. **Developer Experience**: TypeScript, hot reload, better tooling

## Next Steps

1. Complete remaining feature pages
2. Add data tables with sorting/filtering
3. Integrate map library for GPS tracking
4. Add file upload functionality
5. Implement image compression
6. Add loading states and error boundaries
7. Write tests
8. Deploy to production

## Troubleshooting

### Frontend won't start
- Check Node.js version (20.19+ or 22.12+)
- Delete `node_modules` and `package-lock.json`, run `npm install`
- Check for port conflicts (3000 or 5173)

### Backend won't start
- Activate virtual environment
- Install backend requirements: `pip install -r backend/requirements.txt`
- Check database connection
- Check for port conflicts (8000)

### CORS errors
- Ensure backend CORS middleware allows frontend origin
- Check `VITE_API_URL` in frontend `.env`

### Authentication fails
- Check database has users table
- Verify credentials
- Check SECRET_KEY in backend

## Support

For issues or questions, contact: hebtron25@gmail.com

---

© 2025 Hebtron Technologies. All rights reserved.