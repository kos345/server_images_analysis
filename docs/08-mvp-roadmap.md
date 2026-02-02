# Roadmap разработки (MVP → расширение)

## MVP (цель: “end-to-end” один образ → отчет + KG)

### Этап A — каркас проекта и интерфейсы

- структура пакета `agent_triage/`
- CLI `analyze`
- конфиг/ENV, secrets
- создание `triage/<run>/` и `state.json`

### Этап B — ingest + OS detection + read-only mount

- `qemu-img` convert to raw (auto/always/never)
- mount strategy (guestmount) + проверки безопасности
- извлечение `/etc/os-release` и stop-if-not-linux

### Этап C — Filesystem Triage (минимальный артефактный набор)

- OS/Host/Network
- Users/Groups/SSH config/authorized_keys
- Shell histories
- cron/systemd units (минимум)
- heuristics “нестандартные файлы” (top suspicious directories)
- нормализация → `entities.json`/`relations.json`/`findings.json`

### Этап D — Log Agent (auth/ssh successful)

- парсинг auth.log/secure (+ rotated, если успеем)
- агрегация `User↔IP`
- выделение публичных IP

### Этап E — IP enrichment (ipinfo bulk)

- bulk + кеш
- нормализация → KG сущности

### Этап F — Neo4j ingestion

- схема (constraints/indexes)
- upsert сущностей/отношений + provenance
- smoke queries (статистика)

### Этап G — Analyst (GraphRAG) + Report

- retrieval подграфа run
- генерация summary + IoC + evidence
- `report.md` + `report.json`

## Расширение (после MVP)

- поддержка `vmdk/vdi`, nbd mount
- расширенный парсинг пакетов (rpm офлайн), systemd journal (если доступно)
- анализ веб-логов, docker logs
- YARA/ClamAV интеграция (опционально)
- векторный слой в Neo4j для текстов конфигов/скриптов
- REST API + очереди
- (опционально) cross-case correlation — сейчас **не требуется**, так как кейсы изолированы

