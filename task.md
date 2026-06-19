# Задание для LLM-агента: MVP backend платформы MediConnect

Нужно реализовать backend MVP платформы MediConnect: универсальной платформы для безопасного обмена медицинскими данными между пациентами, врачами и медицинскими учреждениями.

## Стек

- Python 3.11+
- FastAPI
- MongoDB как основная БД
- S3-compatible storage через MinIO
- Docker Compose для единоразового запуска всего проекта
- JWT-аутентификация
- Pydantic v2
- Motor / Beanie или другой async MongoDB ODM
- pytest для базовых тестов

## Важно

- Не нужно конвертировать медицинские файлы к единому формату.
- Файлы, включая PDF, JPG, PNG, DICOM, ZIP, XML, JSON и другие, нужно сохранять как есть.
- Файлы должны храниться отдельно от MongoDB, в S3/MinIO.
- Доступ к файлам должен идти только через backend. Не выдавать пользователям прямые публичные ссылки на S3.
- Хранилище MinIO не должно быть публичным для пользователей.
- MVP должен запускаться одной командой: `docker compose up --build`.
- Нужно дать README с описанием запуска и тестовыми сценариями.
- Не строить микросервисную архитектуру для MVP. Один FastAPI-сервис плюс MongoDB и MinIO достаточно для проверки основных пайплайнов.

## Основные роли

### 1. patient

- может загружать свои документы;
- может видеть свои документы;
- может выдавать и отзывать доступ врачу к своим документам;
- может скачивать свои документы через backend.

### 2. doctor

- может видеть документы пациентов, к которым получил доступ;
- может загружать документы пациенту, если имеет доступ или если пациент указан как связанный с врачом;
- может скачивать доступные ему документы через backend;
- не может видеть документы без разрешения.

### 3. admin

- может видеть пользователей, документы и аудит;
- может управлять пользователями;
- может просматривать метаданные документов;
- может скачивать документы через backend;
- имеет административный доступ к системе, но обычные пользователи не должны иметь доступа к MinIO напрямую.

## Сущности MongoDB

### 1. users

Поля:

- `_id`: ObjectId
- `email`: str, unique
- `password_hash`: str
- `full_name`: str
- `role`: enum [`patient`, `doctor`, `admin`]
- `is_active`: bool
- `created_at`: datetime
- `updated_at`: datetime

Для doctor:

- `specialization`: optional str
- `institution_id`: optional ObjectId
- `license_number`: optional str

Для patient:

- `birth_date`: optional date
- `phone`: optional str

Индексы:

- `email` unique
- `role`

### 2. institutions

Поля:

- `_id`: ObjectId
- `name`: str
- `address`: optional str
- `created_at`: datetime
- `updated_at`: datetime

### 3. medical_documents

Поля:

- `_id`: ObjectId
- `patient_id`: ObjectId
- `uploaded_by_user_id`: ObjectId
- `uploaded_by_role`: str
- `institution_id`: optional ObjectId
- `title`: str
- `description`: optional str
- `document_type`: enum или str
  - Примеры: `doctor_report`, `lab_result`, `ct_scan`, `mri_scan`, `xray`, `dicom`, `other`
- `diagnosis`: optional str
- `diagnosis_code`: optional str
- `file`:
  - `bucket`: str
  - `object_key`: str
  - `original_filename`: str
  - `content_type`: str
  - `size_bytes`: int
  - `sha256`: str
- `metadata`: dict
  - Гибкое поле для любых дополнительных медицинских данных.
- `status`: enum [`active`, `deleted`]
- `created_at`: datetime
- `updated_at`: datetime

Индексы:

- `patient_id`
- `uploaded_by_user_id`
- `document_type`
- `created_at`
- `file.sha256`

### 4. document_access_grants

Поля:

- `_id`: ObjectId
- `document_id`: ObjectId
- `patient_id`: ObjectId
- `granted_to_user_id`: ObjectId
- `granted_by_user_id`: ObjectId
- `access_level`: enum [`read`]
- `expires_at`: optional datetime
- `revoked_at`: optional datetime
- `created_at`: datetime

Индексы:

- `document_id`
- `patient_id`
- `granted_to_user_id`
- `revoked_at`

### 5. audit_logs

Поля:

- `_id`: ObjectId
- `actor_user_id`: optional ObjectId
- `actor_role`: optional str
- `action`: str
  - Примеры:
    - `user.registered`
    - `auth.login`
    - `document.uploaded`
    - `document.downloaded`
    - `document.metadata_viewed`
    - `access.granted`
    - `access.revoked`
    - `admin.user_updated`
- `target_type`: optional str
- `target_id`: optional ObjectId
- `ip_address`: optional str
- `user_agent`: optional str
- `details`: dict
- `created_at`: datetime

Индексы:

- `actor_user_id`
- `action`
- `target_type + target_id`
- `created_at`

## API endpoints

### Auth

#### POST /auth/register

Регистрация пользователя.
Для MVP можно разрешить регистрацию `patient` и `doctor`.
Admin создается seed-скриптом при старте.

#### POST /auth/login

Возвращает access_token JWT.

#### GET /auth/me

Возвращает текущего пользователя.

### Users

#### GET /users/me

Текущий пользователь.

#### PATCH /users/me

Обновление профиля.

#### GET /admin/users

Только admin. Список пользователей.

#### PATCH /admin/users/{user_id}

Только admin. Изменение `is_active`, `role`, `institution_id` и базовых данных.

### Institutions

#### POST /admin/institutions

Только admin.

#### GET /institutions

Авторизованные пользователи.

### Documents

#### POST /documents

`multipart/form-data`.

Поля:

- `file`: UploadFile
- `patient_id`: optional str
  - Если загружает patient, можно не передавать, используется текущий пользователь.
  - Если загружает doctor/admin, обязательно указать `patient_id`.
- `title`: str
- `description`: optional str
- `document_type`: str
- `diagnosis`: optional str
- `diagnosis_code`: optional str
- `metadata_json`: optional str, JSON-строка

Поведение:

- проверить права;
- посчитать sha256;
- сохранить файл в MinIO с `object_key` вида `medical-documents/{patient_id}/{document_id}/{safe_filename}`;
- сохранить метаданные в MongoDB;
- записать audit log.

#### GET /documents

Список документов, доступных текущему пользователю.

Для patient: свои документы.
Для doctor: документы, к которым есть active grant.
Для admin: все документы.

Фильтры:

- `patient_id`
- `document_type`
- `diagnosis_code`
- `created_from`
- `created_to`

#### GET /documents/{document_id}

Получить метаданные документа.
Файл не возвращать.

#### GET /documents/{document_id}/download

Скачать файл через backend.
Backend должен читать объект из MinIO и отдавать `StreamingResponse`.
Нельзя возвращать публичную S3-ссылку.
Записать audit log `document.downloaded`.

#### DELETE /documents/{document_id}

Soft delete.
Patient может удалить свой документ.
Admin может удалить любой.
Doctor не может удалять чужой документ, если не admin.

### Access grants

#### POST /documents/{document_id}/access-grants

Только patient-владелец документа или admin.

Body:

- `granted_to_user_id`: str
- `expires_at`: optional datetime

Проверить, что `granted_to_user_id` имеет роль doctor.
Создать grant.
Записать audit log.

#### GET /documents/{document_id}/access-grants

Patient-владелец или admin.
Список активных и отозванных доступов.

#### DELETE /documents/{document_id}/access-grants/{grant_id}

Patient-владелец или admin.
Проставить `revoked_at`.
Записать audit log.

### Audit

#### GET /admin/audit-logs

Только admin.

Фильтры:

- `actor_user_id`
- `action`
- `target_type`
- `target_id`
- `created_from`
- `created_to`

### Health

#### GET /health

Проверить API.

#### GET /health/ready

Проверить соединения с MongoDB и MinIO.

## Авторизация и права доступа

Нужно реализовать dependency:

- `get_current_user`
- `require_role(...)`
- `check_document_access(document, user)`

Правила доступа:

- admin имеет полный доступ через backend.
- patient имеет доступ только к документам, где `document.patient_id == current_user.id`.
- doctor имеет доступ к документу только если существует active grant:
  - `document_id == target document`
  - `granted_to_user_id == doctor.id`
  - `revoked_at is null`
  - `expires_at is null` или `expires_at > now`
- загрузка doctor для patient разрешена только если doctor уже имеет активный доступ хотя бы к одному документу пациента или если есть отдельная связь doctor-patient. Для MVP можно упростить: doctor может загрузить документ пациенту только при наличии активного grant к любому документу этого пациента.
- все действия с документами и доступами пишутся в `audit_logs`.

## S3/MinIO

Docker Compose должен содержать:

- `api`
- `mongodb`
- `minio`
- `minio-init`, который создает private bucket, например `mediconnect-documents`

Настройки через env:

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

Bucket не должен быть public.
API не должен отдавать presigned URL пользователям.
Скачивание только через `/documents/{document_id}/download`.

## Безопасность MVP

Реализовать:

- password hashing через passlib/bcrypt или argon2;
- JWT Bearer auth;
- RBAC;
- audit logs;
- проверку размера файла;
- allowlist content types можно сделать мягкой: сохранять `content_type`, но не блокировать неизвестные типы, если это MVP;
- sha256 файла;
- soft delete документов;
- CORS для локальной разработки.

Ограничения файла:

- `MAX_UPLOAD_SIZE_MB` через env, по умолчанию 100 МБ.
- При превышении вернуть 413.

## Структура проекта

Примерная структура:

```text
app/
  main.py
  core/
    config.py
    security.py
    dependencies.py
    exceptions.py
  db/
    mongo.py
    indexes.py
  models/
    user.py
    institution.py
    medical_document.py
    access_grant.py
    audit_log.py
  schemas/
    auth.py
    user.py
    institution.py
    document.py
    access_grant.py
    audit_log.py
  repositories/
    users.py
    documents.py
    access_grants.py
    audit_logs.py
    institutions.py
  services/
    auth_service.py
    document_service.py
    storage_service.py
    access_service.py
    audit_service.py
  api/
    routes/
      auth.py
      users.py
      admin.py
      institutions.py
      documents.py
      access_grants.py
      audit.py
      health.py
  seed.py

tests/
  test_auth.py
  test_documents_access.py
  test_document_upload_download.py

docker-compose.yml
Dockerfile
requirements.txt или pyproject.toml
.env.example
README.md
```

## Что должно быть в README

Описать:

1. Как запустить:

```bash
docker compose up --build
```

2. Где доступен API:

```text
http://localhost:8000
```

3. Где Swagger:

```text
http://localhost:8000/docs
```

4. Тестовый admin:

email/password из `.env.example`.

5. Проверочный MVP-сценарий:

- зарегистрировать patient;
- зарегистрировать doctor;
- залогиниться patient;
- загрузить документ;
- убедиться, что doctor не видит документ;
- patient выдает доступ doctor;
- doctor видит документ;
- doctor скачивает документ через backend;
- patient отзывает доступ;
- doctor больше не видит документ;
- admin видит audit logs.

6. Как запустить тесты:

```bash
docker compose exec api pytest
```

## Критерии готовности

MVP считается готовым, если:

- `docker compose up --build` поднимает API, MongoDB и MinIO;
- Swagger доступен;
- можно зарегистрировать patient и doctor;
- admin создается автоматически;
- можно загрузить файл;
- файл физически сохраняется в MinIO;
- метаданные сохраняются в MongoDB;
- скачать файл можно только через backend;
- doctor не имеет доступа без grant;
- patient может выдать и отозвать доступ doctor;
- audit logs пишутся для загрузки, скачивания, выдачи и отзыва доступа;
- есть базовые тесты на auth, upload/download и access control;
- проект не реализует конвертацию медицинских файлов.
