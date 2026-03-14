FROM node:20-slim
WORKDIR /app
COPY frontend/package.json /app/package.json
RUN npm install
COPY frontend /app
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "-H", "0.0.0.0", "-p", "3000"]
