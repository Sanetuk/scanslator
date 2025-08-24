# Stage 1: Build the Vue.js application
FROM node:20-alpine as build-stage

WORKDIR /app

# Copy package.json and package-lock.json (or yarn.lock) to install dependencies
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY . .

# Build the Vue.js application for production
# Ensure VITE_APP_BACKEND_API_URL is set during build
ARG VITE_APP_BACKEND_API_URL
ENV VITE_APP_BACKEND_API_URL=$VITE_APP_BACKEND_API_URL

# Print the environment variable to debug
RUN echo "VITE_APP_BACKEND_API_URL is: '$VITE_APP_BACKEND_API_URL'"

RUN npm run build

# Stage 2: Serve the built application with Nginx
FROM nginx:alpine as production-stage

# Copy the custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built assets from the build-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Expose port 80 for the web server
EXPOSE 80

# Command to start Nginx
CMD ["nginx", "-g", "daemon off;"]