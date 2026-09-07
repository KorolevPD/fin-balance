FROM node:18-alpine AS frontend-build

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
ARG REACT_APP_API_URL=/api
ENV REACT_APP_API_URL=${REACT_APP_API_URL}
RUN npm run build

FROM nginx:1.25-alpine

COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY --from=frontend-build /app/build /usr/share/nginx/html
