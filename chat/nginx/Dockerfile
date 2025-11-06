# Используем образ Nginx
FROM nginx:alpine

# Копируем наш конфигурационный файл в контейнер
COPY nginx.conf /etc/nginx/nginx.conf

# Открываем порт 80
EXPOSE 80

# Запускаем nginx
CMD ["nginx", "-g", "daemon off;"]
