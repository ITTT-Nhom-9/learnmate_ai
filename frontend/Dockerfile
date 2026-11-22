# ==============================================================================
# Multi-Stage Dockerfile for LearnMate AI - Frontend SPA (React + Vite + Tailwind)
# Stage 1: Build static bundle (node:20-alpine)
# Stage 2: Serve high-performance static files via Nginx Alpine (nginx:alpine)
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Builder - Compile React SPA
# ------------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Cache package manifests for fast layer rebuilding
COPY package*.json ./
RUN npm ci --prefer-offline || npm install

# Copy source code and config files
COPY . .

# Build-time environment arguments (VITE_API_URL can be injected at build time)
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=$VITE_API_URL

# Build production bundle into /app/dist
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Runner - Production Web Server (Nginx Alpine)
# ------------------------------------------------------------------------------
FROM nginx:alpine AS runner

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled SPA bundle from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy optimized Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=20s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
