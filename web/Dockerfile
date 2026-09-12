# Interface do Lastro. Next.js em modo standalone: a imagem final carrega só o
# servidor e o que a aplicação de fato importa, não a node_modules inteira.

# ---- build ----
FROM node:22-alpine AS build

WORKDIR /app

COPY web/package.json web/package-lock.json ./
# --include=dev é necessário: o `next build` roda typecheck sobre a árvore
# inteira, e os arquivos de teste importam vitest e testing-library.
RUN npm ci --include=dev

COPY web/ ./

# A compilação não fala com o backend — as telas buscam dados em tempo de
# requisição. Mesmo assim o valor precisa existir para o typecheck do proxy.
ENV NEXT_TELEMETRY_DISABLED=1 \
    LASTRO_API_URL=http://api:5001
RUN npm run build

# ---- runtime ----
FROM node:22-alpine AS runtime

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Dentro da rede do compose o serviço de cálculo atende pelo nome `api`,
# não por localhost. O proxy do Next lê esta variável (web/lib/api/proxy.ts).
ENV LASTRO_API_URL=http://api:5001

RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=build --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
