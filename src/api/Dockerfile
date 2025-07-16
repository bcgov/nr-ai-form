# Multi-stage build for Node.js/TypeScript API
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY tsconfig.json ./
COPY src ./src

RUN npm run build

FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --production && npm cache clean --force

COPY --from=build /app/dist ./dist

EXPOSE 3000
CMD ["npm", "start"]
