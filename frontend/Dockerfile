# Stage 1: Build the frontend application
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
ARG VITE_API_BASE_URL
ARG VITE_WS_BASE_URL
# If VITE_URL args are provided, they override the ones in .env.production
RUN if [ -n "$VITE_API_BASE_URL" ]; then export VITE_API_BASE_URL=$VITE_API_BASE_URL; fi && \
    if [ -n "$VITE_WS_BASE_URL" ]; then export VITE_WS_BASE_URL=$VITE_WS_BASE_URL; fi && \
    npm run build

# Stage 2: Serve the static files using Nginx
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
