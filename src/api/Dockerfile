FROM node:20-alpine AS base

# Set working directory
WORKDIR /app

# Install dependencies first (for better layer caching)
COPY package.json package-lock.json* ./

# Install dependencies with clean slate
RUN npm ci

# Copy the rest of the code
COPY . .

# Build the app
RUN npm run build

# Production image, copy all the files and run
FROM node:20-alpine AS production

# Set NODE_ENV
ENV NODE_ENV=production

# Create app directory
WORKDIR /app

# Install only production dependencies
COPY package.json package-lock.json* ./
RUN npm ci --only=production

# Copy built app from build stage
COPY --from=base /app/dist ./dist

# Copy additional necessary files
COPY --from=base /app/src/views ./src/views
#COPY --from=base /app/src/public ./src/public

# Create a non-root user
RUN addgroup -S appuser && adduser -S -G appuser appuser
USER appuser

# Expose port
EXPOSE 3000

# Command to run the app
CMD ["node", "dist/index.js"]
