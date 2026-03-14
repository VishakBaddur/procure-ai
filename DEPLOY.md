# Deploying to Render.com (Free Tier)

This guide walks you through deploying the **backend** and **frontend** to Render.com, including every step and the environment variables you need.

---

## 1. Prerequisites

- A [Render](https://render.com) account (free).
- Your code in a **Git repository** (GitHub, GitLab, or Bitbucket). Render deploys from Git.
- (Optional) [Docker](https://docs.docker.com/get-docker/) installed locally to test with `docker-compose` before deploying.

---

## 2. Local test with Docker (optional)

From the project root:

```bash
docker compose up --build
```

- **Frontend:** http://localhost:3000  
- **Backend:** http://localhost:8000  

The frontend is built with `VITE_API_URL=http://localhost:8000` so it talks to the backend on your machine.

---

## 3. Deploy backend to Render (Web Service)

### 3.1 Create the backend service

1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → **Web Service**.
3. Connect your Git repo and select the repository that contains this project.
4. Configure:
   - **Name:** e.g. `procure-ai-backend`
   - **Region:** choose the one closest to you.
   - **Branch:** `main` (or your default branch).
   - **Root Directory:** leave empty (we’ll set build/start in the next step).
   - **Runtime:** **Docker**.
   - **Dockerfile Path:** `backend/Dockerfile` (relative to repo root).
   - **Instance Type:** **Free**.

### 3.2 Build & start (Docker)

- Render will use `backend/Dockerfile` and run the backend as a Web Service.
- The Dockerfile exposes `PORT`; Render sets `PORT` automatically, and the app uses it.

No need to set a custom build or start command when using the Dockerfile.

### 3.3 Backend environment variables

In the Render service → **Environment** tab, add:

| Variable          | Required | Description |
|-------------------|----------|-------------|
| `PORT`            | No       | Set by Render; app reads it. |
| `GROQ_API_KEY`    | No*      | For AI (quote parsing, etc.) when Ollama isn’t used. Get from [Groq](https://console.groq.com). |
| `SERPAPI_KEY`     | No*      | For vendor research (Google Reviews). Get from [SerpAPI](https://serpapi.com). Without it, research shows “add SerpAPI key to enable”. |
| `GEMINI_API_KEY`  | No       | Optional; for enhanced analysis if you use Gemini. |
| `DB_TYPE`         | No       | `sqlite` (default) or `postgres`. Free tier usually uses SQLite. |
| `DATABASE_URL`    | Yes if Postgres | Only if `DB_TYPE=postgres`. From Render PostgreSQL or another provider. |
| `FRONTEND_ORIGIN` | No       | Your Render frontend URL (e.g. `https://procure-ai-frontend.onrender.com`) so the backend allows CORS from it. |

\* App runs without these; features that need them will be limited or show a message.

**Optional (for PostgreSQL):**

- Create a **PostgreSQL** database on Render (free tier).
- Copy the **Internal Database URL**.
- Set `DB_TYPE=postgres` and `DATABASE_URL=<that URL>`.

### 3.4 Deploy and get backend URL

1. Click **Create Web Service**.
2. Wait for the first deploy to finish.
3. In the service page, copy the **URL**, e.g. `https://procure-ai-backend.onrender.com`.  
   This is your **backend URL**; you’ll use it for the frontend.

---

## 4. Deploy frontend to Render (Static Site)

### 4.1 Create the static site

1. In Render Dashboard: **New +** → **Static Site**.
2. Connect the **same** Git repo.
3. Configure:
   - **Name:** e.g. `procure-ai-frontend`
   - **Branch:** `main` (or your default).
   - **Root Directory:** `frontend`
   - **Build Command:** `npm install && npm run build`
   - **Publish Directory:** `dist`

### 4.2 Frontend environment variables (build-time)

In the Static Site → **Environment** tab, add:

| Variable        | Required | Description |
|-----------------|----------|-------------|
| `VITE_API_URL`  | Yes      | Your **backend URL** from step 3.4, e.g. `https://procure-ai-backend.onrender.com` (no trailing slash). |

This is baked into the frontend at **build time**, so the browser will call your Render backend.

### 4.3 Deploy

1. Click **Create Static Site**.
2. After the build, Render gives you a URL like `https://procure-ai-frontend.onrender.com`.

Open that URL; the app should load and use the backend you deployed in step 3.

---

## 5. CORS (if you see blocklisted requests)

The backend already allows origins via FastAPI CORS. If your frontend is on a different domain and you see CORS errors:

- In `backend/main.py`, ensure `allow_origins` (or equivalent) includes your Render frontend URL, e.g. `https://procure-ai-frontend.onrender.com`, or use `["*"]` for a quick test.

---

## 6. Summary checklist

**Backend (Web Service, Docker)**  
- [ ] Repo connected, Dockerfile path: `backend/Dockerfile`  
- [ ] Env: `GROQ_API_KEY`, `SERPAPI_KEY` (optional but recommended)  
- [ ] Env: `DB_TYPE` and `DATABASE_URL` only if using Postgres  
- [ ] Backend URL copied for frontend  

**Frontend (Static Site)**  
- [ ] Root: `frontend`, Build: `npm install && npm run build`, Publish: `dist`  
- [ ] Env: `VITE_API_URL` = backend URL (no trailing slash)  

**After deploy**  
- [ ] Open frontend URL; create a project and run a flow that calls the API  
- [ ] If something fails, check Render **Logs** for backend and **build logs** for frontend  

---

## 7. Free tier limits (Render)

- **Web Service:** spins down after ~15 min inactivity; first request after that can be slow (cold start).
- **Static Site:** no spin-down; always fast.
- **PostgreSQL:** free tier has row/usage limits; SQLite in the container is fine for light use and doesn’t need a separate DB.

---

## 8. Optional: run both with Docker Compose locally

From the repo root:

```bash
docker compose up --build
```

- Frontend: http://localhost:3000 (built with `VITE_API_URL=http://localhost:8000`)  
- Backend: http://localhost:8000  

To point the frontend at a deployed backend, build with:

```bash
cd frontend && VITE_API_URL=https://procure-ai-backend.onrender.com npm run build
```

Then serve the `dist` folder with any static file server.
