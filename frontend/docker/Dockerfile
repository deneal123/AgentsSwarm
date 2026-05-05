FROM node:20-alpine AS base

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY . .
RUN chmod +x docker/docker-entrypoint.sh

FROM base AS dev

ENTRYPOINT ["/app/docker/docker-entrypoint.sh"]
CMD ["npm", "start"]

FROM base AS builder

ENV REACT_APP_API_BASE_URL=${SERVICE__REACT_APP_API_BASE_URL}
ENV REACT_APP_WS_BASE_URL=${SERVICE__REACT_APP_WS_BASE_URL}
RUN npm run build

FROM nginx:1.27-alpine AS runtime

COPY --from=builder /app/build /usr/share/nginx/html
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
