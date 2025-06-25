FROM node:16-alpine as build

# Imposta la directory di lavoro
WORKDIR /app

# Copia package.json e package-lock.json
COPY package*.json ./

# Installa le dipendenze
RUN npm ci

# Copia il resto dei file
COPY . .

# Genera i file CSS di Tailwind e costruisce l'app
RUN npm run tailwind:build && npm run build

# Stage 2 - Nginx per servire l'applicazione
FROM nginx:alpine

# Copia la build dal primo stage
COPY --from=build /app/build /usr/share/nginx/html

# Copia la configurazione di nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Espone la porta 80
EXPOSE 80

# Avvia nginx
CMD ["nginx", "-g", "daemon off;"] 