#Stage 1 : build the react app
FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: serve with nginx
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
# use /app/build instead of /app/dist if you're on Create React App, not Vite

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
