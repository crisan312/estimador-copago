FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install --frozen-lockfile || npm install

FROM node:20-alpine AS builder
WORKDIR /app
# URL pública de la API — se hornea en el bundle del navegador.
# Vacío (docker-compose) → URLs relativas vía nginx. En Render → URL del api.
ARG NEXT_PUBLIC_API_URL=""
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV production

RUN addgroup --system --gid 1001 nodejs && \
    adduser  --system --uid 1001 nextjs

# public/ siempre existe (contiene .gitkeep) — COPY no admite redirección de shell
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
# HOSTNAME=0.0.0.0 → el server standalone de Next.js escucha en todas las
# interfaces (necesario en Render). PORT no se fija: lo inyecta Render; en
# docker-compose, Next.js usa 3000 por defecto.
ENV HOSTNAME=0.0.0.0
CMD ["node", "server.js"]
