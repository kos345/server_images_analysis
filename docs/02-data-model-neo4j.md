# Модель данных Neo4j (Knowledge Graph) + GraphRAG

## 1) Назначение графа

Neo4j хранит:

- нормализованные сущности (пользователи, файлы, сервисы, IP, события SSH, пакеты…),
- связи между ними,
- provenance (откуда взялись данные, какой запуск, какой артефакт),
- “findings” и IoC.

На базе графа реализуется **GraphRAG**:

- структурный retrieval по подграфу (сущности, соседи, paths),
- гибрид: граф + векторный индекс для текстов (опционально),
- генерация объяснимых выводов (LLM получает только факты + subgraph evidence).

## 2) Принципы моделирования

- **Idempotent upsert**: повторный ingestion одного и того же run не плодит дубликаты.
- **Provenance-first**: каждое утверждение можно отследить до файла/лога/строки.
- **Separation of concerns**:
  - `Run` и `Artifact` — “контейнеры доказательств”
  - domain-узлы — “сущности системы”
  - `Finding`/`IOC` — “аналитические выводы”, привязанные к evidence/subgraph.

## 3) Основные labels (узлы)

### Контейнеры/контекст

- `Run {id, started_at, image_name, image_path, profile, tool_versions...}`
- `Artifact {id, run_id, kind, path, sha256, created_at}`

### Система/ОС

- `Host {id, hostname, distro, version, kernel, arch}`
- `NetworkInterface {id, name, mac, ipv4, ipv6}`
- `Service {id, name, manager, unit_path, enabled, active, listen_ports[]}`
- `Package {id, name, version, source, installed_at?}`
- `DockerImage {id, name, tag, digest}`
- `DockerContainer {id, name, image, created_at?}`
- `CronJob {id, owner, schedule, command, source_path}`

### Пользователи/доступ

- `User {id, username, uid, gid, home, shell}`
- `Group {id, name, gid}`
- `SSHKey {id, kind, fingerprint, comment?}`

### Файлы/артефакты ФС

- `File {id, path, type, mode, uid, gid, size, mtime, sha256?}`
- `Directory {id, path, mode, uid, gid, mtime}`

### События (MVP: SSH)

- `SSHLoginEvent {id, ts, auth_method, success=true, src_ip, src_port?, user, sshd_pid?, raw_line_hash}`

### IP enrichment

- `IP {id, ip, is_public, version}`
- `ASN {id, asn, name?}`
- `Geo {id, country, region?, city?, lat?, lon?}`
- `Org {id, name}`
- `PrivacyFlag {id, vpn?, proxy?, tor?, hosting?}`

### Аналитика

- `Finding {id, title, severity, confidence, category, created_at}`
- `IOC {id, type, value, confidence, first_seen?, last_seen?}`

## 4) Связи (relationships)

### Контекст/происхождение

- `(Run)-[:PRODUCED]->(Artifact)`
- `(Artifact)-[:MENTIONS]->(User|File|Service|IP|...)` (опционально, если есть явное упоминание)
- `(Entity)-[:EVIDENCED_BY]->(Artifact) {offset?, line?, snippet_hash?}`

### Host graph

- `(Run)-[:ANALYZED]->(Host)`
- `(Host)-[:HAS_USER]->(User)`
- `(User)-[:MEMBER_OF]->(Group)`
- `(User)-[:HAS_SSH_KEY]->(SSHKey)`
- `(Host)-[:HAS_SERVICE]->(Service)`
- `(Host)-[:HAS_PACKAGE]->(Package)`
- `(Host)-[:HAS_INTERFACE]->(NetworkInterface)`
- `(Host)-[:HAS_DOCKER_IMAGE]->(DockerImage)`
- `(Host)-[:HAS_DOCKER_CONTAINER]->(DockerContainer)`
- `(Host)-[:HAS_CRON]->(CronJob)`

### Filesystem

- `(Host)-[:HAS_FILE]->(File)`
- `(Host)-[:HAS_DIR]->(Directory)`
- `(User)-[:OWNS]->(File|Directory)` (можно через uid/gid)

### SSH events

- `(Host)-[:HAS_EVENT]->(SSHLoginEvent)`
- `(User)-[:LOGGED_IN]->(SSHLoginEvent)`
- `(SSHLoginEvent)-[:FROM_IP]->(IP)`
- `(User)-[:LOGGED_IN_FROM]->(IP) {first_seen, last_seen, count}` (агрегация)

### IP enrichment

- `(IP)-[:HAS_ASN]->(ASN)`
- `(IP)-[:HAS_GEO]->(Geo)`
- `(IP)-[:HAS_ORG]->(Org)`
- `(IP)-[:HAS_PRIVACY]->(PrivacyFlag)`

### Findings/IoC evidence

- `(Finding)-[:ABOUT]->(User|File|Service|IP|SSHLoginEvent|Package|DockerContainer|Host)`
- `(Finding)-[:SUPPORTED_BY]->(Artifact) {offset?, line?, snippet_hash?}`
- `(IOC)-[:OBSERVED_IN]->(Artifact)`
- `(IOC)-[:LINKED_TO]->(User|File|Service|IP|SSHLoginEvent|Host)`

## 5) Идентификаторы (id strategy)

Рекомендовано:

- `Run.id = uuid`
- `Host.id = sha256(image_hash + ":" + hostname + ":" + distro)` (или просто uuid для run-scoped host)
- `User.id = run_id + ":" + username`
- `File.id = run_id + ":" + path`
- `Service.id = run_id + ":" + name + ":" + unit_path?`
- `IP.id = ip` (глобальный, общий между runs)
- `SSHLoginEvent.id = run_id + ":" + sha256(raw_line)` (или ts+pid+ip+user)

## 6) Индексы/ограничения (Neo4j)

MVP-минимум:

- constraint unique: `Run(id)`, `Artifact(id)`, `User(id)`, `File(id)`, `Service(id)`, `SSHLoginEvent(id)`, `IOC(id)`
- index: `IP(ip)`, `Host(hostname)`, `File(path)`, `User(username)`

## 7) GraphRAG retrieval (MVP)

### 7.1 Retrieval задачи

Запросы аналитика должны уметь:

- получить “подграф” вокруг `Host` конкретного `run_id`,
- построить paths “User → SSHLoginEvent → IP → ASN/Geo/Org”,
- найти аномалии:
  - root logins из публичных IP,
  - входы в нестандартное время,
  - пользователи без home/shell или с необычным shell,
  - сервисы, не соответствующие установленным пакетам,
  - подозрительные файлы в `/tmp`, `/var/tmp`, `/dev/shm`, `~/.ssh/`, cron.

### 7.2 Как LLM получает контекст

LLM получает:

- список релевантных узлов/связей (структурировано),
- короткие “evidence snippets” (строки логов/конфига) с ссылкой на `Artifact`.

LLM не получает полный дамп логов/файлов.

## 8) Векторный слой (опционально)

Если потребуется:

- хранить embedding для `Artifact`-текстов (конфиги, юниты, скрипты),
- гибридный поиск: сначала по графу сущностей, затем по вектору “похожие фрагменты”.

В MVP это можно отложить, оставив “точку расширения”.

