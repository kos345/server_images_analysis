# Спецификация: AI-мультиагент для анализа образов Linux-серверов (forensic triage + GraphRAG)

## 1) Цель

Разработать **мультиагентную систему на Python** для анализа образов серверов (disk image) на предмет признаков использования сервера злоумышленниками: компрометация, persistence, инструменты, следы атак/разведки/фишинга/сбора данных.  
Система должна:

- принимать образ сервера (qcow2/vmdk/vdi/raw и т.п.), при необходимости конвертировать в `raw`;
- определить, что внутри **Linux** (иначе — завершить анализ);
- собрать артефакты triage (ФС, конфиги, пользователи, сервисы, пакеты, cron, docker и т.д.);
- проанализировать **auth/SSH** лог (MVP) с привязкой к сущностям из triage (пользователи, IP и т.п.);
- извлечь публичные IP и обогатить через **ipinfo bulk**;
- нормализовать результаты в **графовую БЗ (Neo4j)**, сохраняя связи;
- выполнить **GraphRAG** по Neo4j и сгенерировать итоговый отчет: факты, связи, подозрительные артефакты, IoC.

## 2) Почему мультиагентная сеть, а не “один агент”

**Мультиагентная архитектура** нужна, потому что:

- triage (ФС/конфиги) и анализ логов — разные типы источников и эвристик;
- важно “сшивать” сущности/отношения (user ↔ file ↔ service ↔ ssh login ↔ ip ↔ geo/asn) в общую модель;
- оркестратор должен планировать, контролировать выполнение, дедупликацию, устойчивость и качество вывода;
- аналитический агент должен работать уже по KG (GraphRAG) и формировать отчет.

## 3) Обязательные технологии

- **Python**
- **GigaChat как основная LLM**
- **langchain_gigachat**, **langchain**, **langgraph**
- **GraphRAG на базе Neo4j** (Neo4j как KG + retrieval поверх графа и/или гибрид граф+вектор)

## 4) Границы и требования форензики (важно)

- Анализ проводится **офлайн**, без “boot” анализируемой ОС.
- Любое обращение к образу — **read-only** (mount/доступ к файлам только чтение).
- Никакого запуска бинарей из образа.
- Все результаты складываются в `triage/<image_name>_<YYYY-MM-DD>_<uuid>/`.
- Нужно сохранять “сырье” (raw артефакты) и нормализованные сущности.

Подробности в `docs/07-security-and-forensics.md`.

## 5) Высокоуровневый пайплайн

1. **Ingest**
   - Проверка/конверсия образа в raw (опционально через `qemu-img`).
2. **OS Detection**
   - Определение OS-family (только Linux → продолжить).
3. **Triage (FS/Config)**
   - OS/Kernel/Release, hostname
   - network config (interfaces, resolv.conf, routes, cloud-init)
   - users/groups, sudoers, SSH keys
   - shell history (bash/zsh), lastlog/wtmp/btmp
   - services (systemd units, init scripts), нестандартные порты
   - packages (dpkg/rpm/apk), подозрительные
   - cron/systemd timers
   - web servers/app stacks (nginx/apache/php/node/java/…)
   - docker/containers (images/containers/configs)
   - список нестандартных файлов/директорий (heuristics)
4. **Log Analysis (MVP)**
   - Парсинг `auth.log`/`secure` (дистрибутивы)
   - ТОЛЬКО успешные SSH входы
   - Корреляция с user/ip из triage
5. **IP Enrichment**
   - Публичные IP → ipinfo bulk → geo/asn/org/hosting/vpn и т.п.
6. **KG Ingestion**
   - Запись сущностей/связей в Neo4j.
7. **GraphRAG Analysis**
   - Поиск подозрительных связей/паттернов, вывод summary + IoC.
8. **Report**
   - Markdown/HTML/JSON отчет (MVP: Markdown + JSON), см. `docs/06-api-cli.md`.

## 6) Артефактные форматы (контракты)

- **Raw triage outputs**: JSON/NDJSON в `triage/<run>/raw/…`
- **Normalized entities/relations**: JSON в `triage/<run>/normalized/…`
- **Neo4j import**: прямой драйверный ingestion (preferred) + опциональные CSV.
- **Final report**: `triage/<run>/report/report.md` + `report.json`

Схемы в `docs/03-workflows-triage.md` и `docs/02-data-model-neo4j.md`.

## 7) Интерфейсы

MVP:
- CLI: `python -m agent_triage analyze --image path --out triage/...`

Опционально:
- REST API (FastAPI) для интеграций и очередей.

Подробно: `docs/06-api-cli.md`.

## 8) Состав агентов

- **Orchestrator Agent (LangGraph)**: планирует шаги, запускает исполнителей, дедуплицирует, следит за качеством.
- **Filesystem Triage Agent**: извлекает артефакты и первичную нормализацию.
- **Log Agent (Auth/SSH)**: парсит успешные логины, привязывает к сущностям.
- **KG Writer (может быть модулем/узлом)**: upsert в Neo4j, ведет provenance.
- **Analyst Agent (GraphRAG)**: строит гипотезы, ищет связи, формирует вывод.
- **Report Agent**: сборка отчета, таблицы, IoC, ссылки на артефакты.

LangGraph детали: `docs/04-agents-and-langgraph.md`.

## 9) План разработки (MVP → расширение)

См. `docs/08-mvp-roadmap.md`.

## 10) Открытые вопросы (нужно уточнить)

См. `docs/09-open-questions.md`.  
Система проектируется так, чтобы большинство решений можно было “включать” конфигом без ломки архитектуры.

