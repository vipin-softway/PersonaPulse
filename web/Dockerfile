# --- deps ---
FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
# npm install (not ci): follows the lockfile but adds Linux-only optional packages that a
# lockfile generated on macOS leaves out (e.g. @emnapi/* for Tailwind's native engine).
RUN npm install --no-audit --no-fund

# --- build ---
FROM node:24-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Public API URL is inlined into the browser bundle at build time.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# --- run ---
FROM node:24-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=8080 \
    HOSTNAME=0.0.0.0
RUN addgroup -S nodejs && adduser -S nextjs -G nodejs
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
USER nextjs
EXPOSE 8080
CMD ["node", "server.js"]
