FROM node:20-alpine AS build
WORKDIR /app
RUN npm config set registry https://registry.npmjs.org
COPY package.json /app/package.json
RUN npm install --registry=https://registry.npmjs.org --no-audit --no-fund
COPY . /app
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
