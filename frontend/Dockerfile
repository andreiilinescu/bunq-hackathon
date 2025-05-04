# ─── Stage 1: Build ───────────────────────────────────────────────────────
FROM node:22-alpine AS build

# Set working dir and install dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --silent

# Copy source & build
COPY . .
RUN npm run build

# ─── Stage 2: Serve ──────────────────────────────────────────────────────
FROM nginx:alpine

# Copy the build artifacts from the previous stage
COPY --from=build /app/dist /usr/share/nginx/html 

# Copy custom Nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port 80
EXPOSE 80

# Launch Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]