# Fase di build
FROM node:18-alpine as build

WORKDIR /app

# Copia package.json e package-lock.json
COPY package*.json ./

# Installa le dipendenze
RUN npm install

# Copia il resto dei file
COPY . .

# Crea la build di produzione
RUN npm run build

# Fase di produzione
FROM nginx:alpine

# Copia i file di build nella directory di nginx
COPY --from=build /app/build /usr/share/nginx/html

# Espone la porta 80
EXPOSE 80

# Avvia nginx
CMD ["nginx", "-g", "daemon off;"] 