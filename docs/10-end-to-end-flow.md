# End-to-end flow агентной сети (LangGraph + tools_src + Neo4j GraphRAG)

Этот документ описывает, что происходит с момента запуска анализа и поступления файла образа, какие узлы выполняются, как взаимодействуют агенты и как используется Neo4j (запись и retrieval).

## 1) Участники (роли)

- **Orchestrator (LangGraph)**: планирует и исполняет граф, держит `state.json`, решает skip/continue/stop.
- **Tool-layer (детерминированные классы из `tools_src/`)**:
  - `ImageProcessor`: определение типа образа, конвертация в raw, метаданные/хеши.
  - `TriageCollector` (pytsk3 + `triage.yaml`): сбор артефактов и выгрузка логов.
  - `ContextEnricher`: ipinfo bulk, VT lookup по SHA256 (опционально), извлечение сущностей.
  - (опционально) `TelegramBot`: отправка результата.
- **LLM stages (GigaChat-2-Max)**:
  - summaries по triage-артефактам (services/cron/apt/logs/files/history),
  - аналитика GraphRAG по подграфу Neo4j (evidence-first).
- **Neo4j**: хранит KG одного кейса (1 образ = 1 кейс) и служит источником retrieval для GraphRAG.

## 2) Артефакты и state

- **Файловые артефакты** пишутся в `triage/<image>_<YYYY-MM-DD>_<uuid>/...` (см. `docs/03-workflows-triage.md`).
- **State-first**: оркестратор ведет `state.json`, где индексирует артефакты, сущности, найденные IP/IoC, статусы шагов.

## 3) Диаграмма узлов/переходов (LangGraph)

```mermaid
flowchart TD
  A([Start: analyze(image)]) --> B[Orchestrator: init state/run_id]
  B --> C[init_case: case_name = case_<image_file_name>]
  C --> D[ingest_image: ImageProcessor\n- detect format\n- qemu-img -> raw (if needed)\n- hashes/metadata]
  D --> E[detect_os: TriageCollector (pytsk3)\n- read /etc/os-release]
  E -->|os != linux| Z([Stop: unsupported_os\nminimal status/report])
  E -->|linux| F[collect_triage: TriageCollector\n- triage dir\n- artifacts via triage.yaml\n- logs/raw\n- auth_full.log\n- history_clear_*]

  F --> G{have auth logs?}
  G -->|no| H1[triage_summaries (LLM)\nservices/cron/apt/logs/root/home/history]
  G -->|yes| H[log_agent_auth_ssh\n- parse auth_full.log\n- success_auth.log\n- extract public IPs]

  H --> I{public IPs?}
  I -->|no| H1
  I -->|yes| J[ip_enrichment: ContextEnricher\n- ipinfo bulk\n- success_auth_IP.json\n- history_*_IP.json]
  J --> H1

  H1 --> K[generate_iocs\n- iocs_full.json\n- iocs_clear.json (optional LLM)]
  K --> L{vt enabled + key?}
  L -->|no| M[kg_upsert: Neo4j\n- normalize entities/relations\n- provenance links]
  L -->|yes| L2[vt_lookup: ContextEnricher\n- lookup by SHA256\n- iocs_vt.json] --> M

  M --> N[graph_rag_analyst (LLM)\n- retrieve subgraph\n- verdict/findings/iocs\n- report_addendum]
  N --> O[render_report\n- Jinja2 HTML\n- include required sections\n- mask secrets]
  O --> P{telegram enabled?}
  P -->|no| Q([Done])
  P -->|yes| R[telegram_notify\n- send summary + files] --> Q
```

## 4) Что делает каждый этап (коротко)

### 4.1 `init_case`

- Определяет “кейс” как **1 образ**.
- Выбирает `case_name` из имени файла образа.
- Фиксирует режим изоляции хранилища кейса:
  - либо отдельная БД Neo4j на кейс,
  - либо отдельный контейнер/инстанс Neo4j (если multiple databases недоступны).

### 4.2 `ingest_image` (ImageProcessor)

- Проверяет формат (raw/qcow2).
- При необходимости конвертирует в raw через `qemu-img`.
- Считает/фиксирует хеши, размер, пути.

### 4.3 `detect_os` (TriageCollector)

- Читает признаки ОС (например `/etc/os-release`) из образа через pytsk3.
- Gate: не Linux → stop.

### 4.4 `collect_triage` (TriageCollector)

- Создает `triage/<image>_<date>_<uuid>/`.
- Собирает артефакты по `triage.yaml` + обязательные файлы по ТЗ заказчика.
- Выгружает логи, готовит `auth_full.log`, чистит history-файлы.
- Пишет audit-логи.

### 4.5 `log_agent_auth_ssh`

- Парсит `auth_full.log`, извлекает только `Accepted ...` события.
- Пишет `success_auth.log`.
- Извлекает публичные IP для enrichment.

### 4.6 `ip_enrichment` (ContextEnricher)

- Делает ipinfo bulk для публичных IP (если включено).
- Пишет `success_auth_IP.json` и файлы обогащения IP из history.

### 4.7 `generate_iocs` / `vt_lookup`

- Формирует IOC JSON по файлам:
  - `iocs_full.json` (hashes + метаданные),
  - `iocs_clear.json` (после фильтрации, опционально).
- Опционально VT lookup **по SHA256** (без загрузки файлов) → `iocs_vt.json`.

### 4.8 `kg_upsert` (Neo4j)

**Когда записываем**: после того как есть triage-артефакты + события SSH + enrichment + IoC (по возможности).

**Что записываем**:
- доменные сущности: Host/User/File/Service/Cron/Package/SSHLoginEvent/IP/Geo/ASN/Org/IOC/Finding;
- связи: например `User-LOGGED_IN_FROM->IP`, `Host-HAS_SERVICE->Service`, `IOC-LINKED_TO->File`;
- provenance: `Entity-EVIDENCED_BY->Artifact` (path + line/offset если доступно).

**Как используем потом**: Neo4j становится источником truth для связей и retrieval.

### 4.9 `graph_rag_analyst`

- Делает retrieval подграфа (host-centric) из Neo4j.
- LLM строит выводы evidence-first:
  - оценка вероятности компрометации,
  - ключевые находки с привязкой к узлам/ребрам/артефактам,
  - IoC и рекомендации.
- Может сформировать `report_addendum` для вставки в HTML.

### 4.10 `render_report` (+ `telegram_notify`)

- Генерирует **HTML** через Jinja2 (`templates/`), включает обязательные секции по ТЗ.
- Маскирует чувствительные данные.
- Опционально отправляет summary + файлы в Telegram.

## 5) Принципы “не хардкодить логику в промпте”

- Оркестратор планирует **узлы и параметры**, а не “пишет алгоритм”.
- Исполнители (tool-layer) реализуют детерминированные шаги.
- LLM используется только для:
  - summaries (на входе конкретные артефакты),
  - GraphRAG аналитики (на входе подграф + evidence snippets).

