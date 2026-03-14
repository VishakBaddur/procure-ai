# Frontend: build with Node, serve with nginx
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --omit=optional 2>/dev/null || npm install

COPY . .

# Set at build time: backend URL for API calls (e.g. http://localhost:8000 for compose, https://your-backend.onrender.com for Render).
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Production: nginx serves static files and proxies /api to backend
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
