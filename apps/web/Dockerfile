FROM node:22-alpine AS deps

WORKDIR /workspace/apps/web

COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

FROM node:22-alpine AS runner

ENV NODE_ENV=development \
    NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000

WORKDIR /workspace/apps/web

COPY --from=deps /workspace/apps/web/node_modules ./node_modules
COPY apps/web ./

EXPOSE 3002

CMD ["npm", "run", "dev"]
