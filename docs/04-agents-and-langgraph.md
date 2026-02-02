# Агенты и LangGraph (контракты, роли, планирование)

## 1) Общая идея

В LangGraph каждый агент реализуется как узел, принимающий **структурированное состояние** и возвращающий **структурированный delta-результат** (обновление state).  
LLM используется для:

- планирования (оркестратор),
- объяснения подозрительности (analyst),
- извлечения/нормализации из текстовых артефактов (в ограниченных местах).

LLM **не должен** “угадывать факты”: факт считается фактом только при наличии evidence (файл/строка/хеш/лог-событие).

## 2) Роли агентов

### 2.1 Orchestrator Agent

**Вход**: `RunState` (image_path, config, уже найденные метаданные)  
**Выход**: план шагов (в рамках графа) + policy:

- какие артефакты собирать (профиль “mvp/extended”),
- какие узлы пропускать,
- какие ограничения применить (например, “no network”, “skip malware scan”).

### 2.2 Filesystem Triage Agent

**Вход**: доступ к смонтированной read-only ФС, config профиля  
**Выход**:

- `ArtifactRecord[]` (где лежит raw output)
- `Entity[]` и `Relation[]` (нормализация)
- `SuspiciousFinding[]` (эвристики + evidence ссылки)

**Примечание**: в MVP агент должен опираться на детерминированные парсеры/шаблоны; LLM — только для классификации “подозрительно/нет” с обязательной ссылкой на evidence.

### 2.3 Log Agent (Auth/SSH)

**Вход**: пути к логам + список известных пользователей/IP/hostnames из triage  
**Выход**:

- `SSHLoginEvent[]` (только successful)
- `Entity(IP/User/Host)` при необходимости
- `Relation` вида `(:User)-[:LOGGED_IN_FROM]->(:IP)` с `first_seen/last_seen/count`

### 2.4 Enrichment Agent (ipinfo)

**Вход**: список публичных IP  
**Выход**:

- `IPEnrichment[]` + соответствующие KG сущности (`ASN`, `Geo`, `Org`, `PrivacyFlag`) и связи.

### 2.5 KG Writer

**Вход**: `Entity[]`/`Relation[]` + provenance  
**Выход**: `neo4j_stats`, `upserted_ids`, `dedup_report`

### 2.6 Analyst Agent (GraphRAG)

**Вход**: `run_id`, цели анализа, список приоритетных IoC/сущностей  
**Выход**:

- `NarrativeSummary` (ссылки на subgraph evidence),
- `Hypothesis[]` (например, “сервер использовался как phishing host”),
- `IOC[]` (IP, домены, пути, хеши, ключи),
- `Recommendations` (следующие шаги, что доисследовать).

## 3) RunState (структура состояния)

MVP-структура должна поддерживать:

- идентификацию запуска (`run_id`, timestamps),
- метаданные образа (путь, формат, hashes),
- доступ к ФС (mount strategy),
- индексы артефактов,
- нормализованные сущности/связи,
- список публичных IP,
- результаты enrichment,
- отчет.

Точная схема задается в `docs/03-workflows-triage.md` (как контракт JSON) и `docs/02-data-model-neo4j.md` (как KG-модель).

## 4) Планирование в LangGraph (как “решает” оркестратор)

Оркестратор управляет графом **не через свободный текст**, а через **структурированный план**, например:

- `steps`: `[detect_os, init_triage_dir, fs_triage, log_auth_ssh, enrich_ip, kg_upsert, graph_rag, report]`
- `flags`: `skip_enrichment_if_no_public_ip=true`, `stop_if_not_linux=true`
- `profiles`: `mvp|extended`

LLM-вывод оркестратора валидируется схемой (Pydantic/JSONSchema). Если невалидно — fallback на дефолтный план.

## 5) Модель “evidence-first”

Каждая находка обязана содержать:

- `evidence_type`: file/log/config/metadata
- `evidence_path` + `offset` (строки/байты по возможности)
- `extract`: кусок текста/строка лога (ограниченный)
- `confidence` и `reasoning` (без утечки секретов)

## 6) Интеграция с LangChain и GigaChat

### 6.1 LLM

- основная модель: **GigaChat**
- LangChain wrapper: `langchain_gigachat`

### 6.2 Где именно нужен LLM в MVP

- классификация подозрительных артефактов (на основе структурированных признаков),
- генерация отчета/summary из уже собранных фактов,
- построение гипотез (analyst) по subgraph retrieval.

### 6.3 Где LLM НЕ нужен

- парсинг стандартных форматов (passwd, shadow, sshd_config, systemd units, auth logs) — лучше детерминированно.

