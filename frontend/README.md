# VTS Report Tool - Frontend

Modern React/TypeScript frontend for the VTS Report Tool, built with Vite, React Router v7, Tailwind v4, and shadcn components.

## Features

- 🔐 JWT Authentication
- 📊 Dashboard with statistics
- 📝 Incident reporting with image uploads
- ⏱️ Idle time analyzer
- ☕ Breaks & pickups management
- 🔍 Report search and filtering
- 🗺️ GPS tracking with maps
- 📈 Accident analysis

## Tech Stack

- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite
- **Routing**: React Router v7
- **Styling**: Tailwind CSS v4
- **Components**: shadcn/ui
- **Icons**: Lucide React
- **HTTP Client**: Axios
- **Authentication**: JWT tokens

## Getting Started

### Prerequisites

- Node.js 20.19+ or 22.12+
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Update `.env` with your API URL:
```
VITE_API_URL=http://localhost:8000/api
```

### Development

Start the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:3000`

### Build

Create a production build:
```bash
npm run build
```

Preview the production build:
```bash
npm run preview
```

## Project Structure

```
frontend/
├── public/              # Static assets
│   └── Kenhalogo.png   # Logo
├── src/
│   ├── components/     # Reusable components
│   │   ├── Header.tsx
│   │   ├── Layout.tsx
│   │   ├── ProtectedRoute.tsx
│   │   └── Sidebar.tsx
│   ├── contexts/       # React contexts
│   │   └── AuthContext.tsx
│   ├── lib/            # Utilities
│   │   └── api.ts      # Axios instance
│   ├── pages/          # Page components
│   │   ├── AccidentAnalysis.tsx
│   │   ├── BreaksPickups.tsx
│   │   ├── Dashboard.tsx
│   │   ├── GPSTracking.tsx
│   │   ├── IdleAnalyzer.tsx
│   │   ├── IncidentReport.tsx
│   │   ├── Login.tsx
│   │   └── ReportSearch.tsx
│   ├── App.tsx         # Main app component
│   ├── index.css       # Global styles & Tailwind
│   ├── main.tsx        # Entry point
│   └── vite-env.d.ts   # TypeScript declarations
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
└── vite.config.ts
```

## Authentication

The app uses JWT token-based authentication:

1. User logs in with contractor, username, and password
2. Backend returns JWT access token
3. Token is stored in localStorage
4. Token is sent with all API requests via Authorization header
5. Token expires after 8 hours

## API Integration

All API calls go through the Axios instance in `src/lib/api.ts`:

- Base URL configured via `VITE_API_URL` environment variable
- Automatic token injection for authenticated requests
- Automatic redirect to login on 401 responses

## Role-Based Access

Different features are available based on user roles:

- **admin**: Full access except accident analysis
- **control**: Access to most features
- **patrol**: Limited access (incidents, breaks/pickups)
- **re_admin**: Full access including accident analysis

## Deployment

### Vercel (Recommended)

1. Push code to GitHub
2. Import project in Vercel
3. Set environment variables:
   - `VITE_API_URL`: Your production API URL
4. Deploy

### Manual Deployment

1. Build the project:
```bash
npm run build
```

2. Deploy the `dist` folder to your hosting service

## Environment Variables

- `VITE_API_URL`: Backend API base URL (default: `http://localhost:8000/api`)

## Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## License

© 2025 Hebtron Technologies. All rights reserved.