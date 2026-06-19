# MediConnect MVP Backend

MVP backend для безопасного обмена медицинскими документами между пациентами, врачами и администратором. Файлы сохраняются как есть в private MinIO bucket, метаданные и права доступа хранятся в MongoDB, скачивание идет только через FastAPI backend.

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

API: `http://localhost:8000`

Swagger: `http://localhost:8000/docs`

Тестовый admin создается автоматически при старте:

```text
email: admin@mediconnect.local
password: admin12345
```

Значения можно изменить в `.env`.

## Проверочный MVP-сценарий

1. Зарегистрировать patient через `POST /auth/register`.
2. Зарегистрировать doctor через `POST /auth/register`.
3. Залогиниться patient через `POST /auth/login`.
4. Загрузить документ patient через `POST /documents` с `multipart/form-data`.
5. Залогиниться doctor и проверить `GET /documents`: список пустой.
6. Patient выдает доступ doctor через `POST /documents/{document_id}/access-grants`.
7. Doctor видит документ через `GET /documents`.
8. Doctor скачивает файл через `GET /documents/{document_id}/download`; backend стримит объект из MinIO и не возвращает S3 URL.
9. Patient отзывает доступ через `DELETE /documents/{document_id}/access-grants/{grant_id}`.
10. Doctor снова вызывает `GET /documents` и больше не видит документ.
11. Admin вызывает `GET /admin/audit-logs` и видит события загрузки, скачивания, выдачи и отзыва доступа.

## Тесты

В запущенном compose:

```bash
docker compose exec api pytest
```

Локально, если зависимости установлены:

```bash
pytest
```

## Основные переменные окружения

- `MONGO_URI`
- `MONGO_DB_NAME`
- `S3_ENDPOINT_URL`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`
- `S3_BUCKET_NAME`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `MAX_UPLOAD_SIZE_MB`

## Ограничения MVP

Сервис не конвертирует медицинские файлы к единому формату. PDF, JPG, PNG, DICOM, ZIP, XML, JSON и другие файлы сохраняются в MinIO без преобразования.
