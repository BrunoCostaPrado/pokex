# Build stage
FROM node:26-alpine AS builder
WORKDIR /app

# Enable corepack for pnpm
RUN corepack enable

# Copy all package files for proper workspace resolution
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/
COPY packages/ui/package.json packages/ui/

# Copy all source for workspace packages
COPY packages/ui packages/ui
COPY apps/web apps/web

# Install dependencies with cache mount
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm approve-builds @biomejs/biome @swc/core esbuild msw --yes && \
    pnpm install --frozen-lockfile --prefer-offline

# Build @pokex/ui first, then web
RUN cd packages/ui && pnpm exec tsc && cd ../.. && pnpm run build --filter web

# Runtime stage
FROM nginx:alpine AS runner
WORKDIR /usr/share/nginx/html

# Copy built assets
COPY --from=builder /app/apps/web/dist .

# Copy nginx config
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf

# Non-root user (nginx user exists in nginx:alpine)
USER nginx

EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]