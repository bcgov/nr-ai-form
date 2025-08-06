FROM node:22-alpine AS builder

# Add labels for better maintainability
LABEL maintainer="BCGov" \
      description="NR AI Form API" \
      version="1.0"

WORKDIR /app

# Install dependencies first (better layer caching)
COPY package*.json ./
RUN npm ci

# Copy source files
COPY tsconfig.json ./
COPY src ./src

# Build and verify output directory exists
RUN npm run build && \
    ls -la build || exit 1

# Production image
FROM node:22-alpine AS runner

# Add non-root user for security
RUN addgroup -g 1001 -S nodejs \
    && adduser -S nodeuser -G nodejs

WORKDIR /app

# Copy only production dependencies
COPY package*.json ./
RUN npm ci --only=production && \
    npm cache clean --force

# Copy built assets from builder (use correct output directory)
COPY --from=builder /app/build ./build

# Set proper ownership
RUN chown -R nodeuser:nodejs /app

# Use non-root user
USER nodeuser

# Configure environment
ENV NODE_ENV=production \
    PORT=3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

# Expose port
EXPOSE 3000

# Start application
CMD ["npm", "start"]