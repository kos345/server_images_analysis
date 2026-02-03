1) Что уже есть в репозитории (опора, а не “писать с нуля”)

    Спецификация и контракты: SPECIFICATION.md, docs/01-11*.md.
    Готовый tool-layer (детерминированные операции triage): tools_src/src/:
        core/image_processor.py — формат/конвертация образа в raw через qemu-img
        triage/collector.py — pytsk3 сбор артефактов в triage/<run>/...
        triage/analyzer.py — базовый анализ + HTML-отчет (сейчас без LLM)
        triage/context_enricher.py — извлечение сущностей (IP/домены/хеши); внешние enrich сейчас “заглушки”
    Промпты triage: prompts/triage/*.md, реестр prompts/triage_prompts.py.
    Требования: Python 3.11, langchain_gigachat + langchain + langgraph, Neo4j GraphRAG, evidence-first, read-only.

Цель разработки: добавить “надстройку” agent_triage/ (оркестрация LangGraph + state + нормализация + Neo4j ingestion + GraphRAG аналитика + отчеты), переиспользуя tools_src как tool-layer.

2) Целевая архитектура (как будет работать система)

Style: state-first LangGraph workflow (см. docs/01-architecture.md, docs/04-agents-and-langgraph.md, docs/10-end-to-end-flow.md)
2.1 Узлы LangGraph (MVP)

    init_run — создает run_id, директорию triage/<image>_<YYYY-MM-DD>_<uuid>/, state.json
    ingest_image — ImageProcessor: тип образа, конвертация в raw (если нужно), хеши/метаданные
    detect_os — Linux-only gate (через TriageCollector.detect_os() или чтение /etc/os-release)
    collect_triage — TriageCollector.collect_all() + индекс артефактов
    log_agent_auth_ssh — парсинг logs/clear/auth_full.log → success_auth.log + события SSHLoginEvent
    ip_enrichment — ipinfo bulk + кеш → success_auth_IP.json + сущности ASN/Geo/Org/PrivacyFlag
    normalize — построение normalized/entities.json, relations.json, findings.json, iocs.json (контракт из docs/03-workflows-triage.md)
    kg_upsert — idempotent upsert в Neo4j + provenance (модель из docs/02-data-model-neo4j.md)
    graph_rag_analyst — retrieval подграфа + LLM аналитика evidence-first
    render_report — report.json + report.md (+ опционально report.html через Jinja2)

3) Базовые контракты данных (их нужно “застолбить” в коде сразу)

Реализовать Pydantic-модели (или dataclasses + JSONSchema) в agent_triage/models.py:
3.1 RunState

Минимум поля:

    run_id: str, started_at, status: ok|unsupported_os|error
    image: {input_path, raw_path, format, sha256_input, sha256_raw, size_bytes}
    case: {case_name, neo4j_isolation_mode: database|container}
    paths: {run_dir, raw_dir, normalized_dir, report_dir, logs_dir}
    artifacts_index: list[ArtifactRecord]
    entities/relations/findings/iocs: list[...] (или пути на JSON файлы + stats)
    public_ips: list[str]
    neo4j: {enabled, uri, database?, stats}
    llm_calls_index_path (для NDJSON логов LLM)
    errors/warnings: list[...]

3.2 Нормализованные записи

    ArtifactRecord {id, kind, path, sha256?, created_at}
    Entity {id, label, properties, provenance}
    Relation {type, src_id, dst_id, properties?, provenance}
    Finding {id, title, severity, confidence, category, about_ids[], evidence[]}
    IOC {id, type, value, confidence, evidence[]}
    SSHLoginEvent {id, ts, user, src_ip, src_port?, auth_method, raw_line_hash, provenance}

Важно: provenance везде (см. docs/02-data-model-neo4j.md).

4) Поэтапный план реализации (каждый этап заканчивается проверкой работоспособности)
Этап A — Каркас agent_triage + CLI + state-first логирование

Цель: запускать python -m agent_triage analyze --image ... и получать triage/<run>/state.json даже без Neo4j/LLM.

Сделать

    Создать пакет agent_triage/:
        __init__.py
        cli.py (argparse/typer)
        config.py (ENV + YAML, без секретов в state)
        logging.py (run-scoped logs, audit trail)
        models.py (Pydantic модели из раздела 3)
        state_store.py (load/save state.json, atomic write)
    CLI флаги по docs/06-api-cli.md (минимум: --image, --out, --profile, --convert-to-raw, --neo4j-enabled, --ipinfo-enabled, --vt-enabled).

Проверка

    Unit-тест: создание RunState + сериализация/десериализация.
    Smoke: запуск CLI на несуществующем образе → корректная ошибка, лог, статус error.

Критерий готовности

    Есть стабильный RunState и файловая структура run-директории.

Этап B — Ingest образа (qcow2/raw) + OS-detection gate

Цель: из CLI пройти шаги ingest + detect_os и корректно остановиться, если не Linux.

Сделать

    agent_triage/nodes/ingest_image.py: обертка над tools_src.src.core.ImageProcessor.
    agent_triage/nodes/detect_os.py: использовать tools_src.src.triage.TriageCollector.detect_os() или чтение /etc/os-release через collector.
    Реализовать policy convert-to-raw: auto|always|never (см. docs/03-workflows-triage.md).
    Обязательное логирование версий инструментов (как минимум qemu-img --version, если доступно).

Проверка

    Unit: мок ImageProcessor.get_metadata() → state обновляется ожидаемо.
    Unit: detect_os возвращает linux/None → guard работает.
    Smoke: при not linux создается короткий report.md “unsupported_os”.

Критерий готовности

    Узлы ingest/detect_os устойчивы и детерминированы.

Этап C — Filesystem triage сбор артефактов (через tools_src)

Цель: получить артефакты в структуре из docs/03-workflows-triage.md + заполнить artifacts_index.

Сделать

    agent_triage/nodes/collect_triage.py: вызвать TriageCollector.collect_all(raw_path, image_name).
    После сбора: просканировать ожидаемые выходные файлы и записать в artifacts_index (kind = system_os, users_passwd, logs_auth_full, и т.д.).
    Создать raw/ и normalized/ подкаталоги в run-dir (даже если часть файлов лежит рядом — индексируйте фактические пути).

Проверка

    Unit: на “фиктивной triage-директории” (fixtures) индексатор находит файлы корректно.
    Smoke: при ошибке triage — state фиксирует error, но сохраняется.

Критерий готовности

    Есть воспроизводимый набор артефактов + индекс.

Этап D — Log Agent (MVP: успешные SSH логины)

Цель: из logs/clear/auth_full.log извлечь только Accepted ... события и связать с пользователями/IP.

Сделать

    agent_triage/log_parsers/auth_ssh.py:
        распознать паттерны из docs/03-workflows-triage.md (Accepted password/publickey ...)
        нормализовать SSHLoginEvent
        агрегировать User↔IP (count, first_seen, last_seen)
        сохранить:
            logs/clear/success_auth.log (только строки Accepted)
            normalized/ssh_login_events.json (или в общий entities/relations)
    agent_triage/utils/ip.py: функция is_public_ip(ip) (RFC1918/localhost/link-local/CGNAT исключить).

Проверка

    Unit: парсер на наборе строк (fixtures) → корректные события/поля.
    Unit: фильтрация публичных IP.
    Smoke: если auth_full.log отсутствует — узел пропускается, state содержит warning.

Критерий готовности

    SSH события формируются детерминированно, без LLM.

Этап E — IP enrichment через ipinfo bulk + кеширование

Цель: обогатить публичные IP и сохранить как raw+normalized.

Сделать

    agent_triage/enrichment/ipinfo.py:
        клиент ipinfo bulk (requests/httpx)
        батчинг + retries/backoff
        дисковый кеш: triage/<run>/cache/ipinfo/<ip>.json или общий ipinfo_cache.json
        нормализация в сущности IP/ASN/Geo/Org/PrivacyFlag + связи IP-HAS_*
    Выход: logs/clear/success_auth_IP.json (как в docs/06-api-cli.md) и записи в normalized.

Проверка

    Unit: мок HTTP ответов (без сети) → корректная нормализация.
    Интеграционный smoke (опционально): реальный вызов при наличии IPINFO_TOKEN.

Критерий готовности

    Enrichment полностью опционален (выключается флагом) и не ломает run.

Этап F — Нормализация в entities/relations/findings/iocs (единый контракт)

Цель: собрать все факты в JSON, готовый для Neo4j ingestion и отчета.

Сделать

    agent_triage/normalize/triage_to_kg.py:
        распарсить:
            users/passwd.txt → User, Group (минимум users)
            system/services.txt → Service (минимум список)
            system/cron.txt → CronJob (best-effort)
            system/apt.txt → Package (dpkg: best-effort)
            files/iocs*.json → IOC (hash-only режим)
            logs/clear/success_auth.log → SSHLoginEvent, связи с User и IP
        сформировать Host и связать (Run)-[:ANALYZED]->(Host) как в docs/02-data-model-neo4j.md
        добавить provenance на уровне “какой файл/какая строка”
    Выходные файлы:
        normalized/entities.json, normalized/relations.json, normalized/findings.json, normalized/iocs.json

Проверка

    Unit: на фикстурах triage-файлов → ожидаемое число сущностей/связей.
    Unit: id strategy (см. docs/02-data-model-neo4j.md) стабильна и идемпотентна.

Критерий готовности

    Нормализованный набор данных можно повторно генерировать без изменения id.

Этап G — Neo4j ingestion (идемпотентность + provenance + изоляция кейса)

Цель: записывать в Neo4j и получать “источник правды” для GraphRAG.

Сделать

    agent_triage/neo4j/schema.py: constraints/indexes из docs/02-data-model-neo4j.md
    agent_triage/neo4j/writer.py:
        upsert_entities(entities) через MERGE по id
        upsert_relations(relations) через MATCH + MERGE
        upsert_artifacts(artifacts_index) и связи Run-PRODUCED->Artifact, Entity-EVIDENCED_BY->Artifact
    Изоляция кейса (см. docs/02 + docs/06):
        режим database: использовать neo4j://... + database=case_name (если поддерживается)
        режим container: отдельный инстанс/контейнер на кейс (в MVP можно оставить как “операционная инструкция + конфиг”, а не автозапуск)

Проверка

    Интеграционный тест с Neo4j в Docker (testcontainers или docker-compose):
        прогнать ingestion дважды → количество узлов/ребер не растет (идемпотентность)
        smoke-query: paths User→SSHLoginEvent→IP→ASN
    Unit: генерация cypher и батчинг.

Критерий готовности

    Neo4j реально хранит KG и выдерживает повторный прогон.

Этап H — GraphRAG Analyst (LLM: GigaChat) + обязательное LLM-логирование

Цель: evidence-first аналитика по подграфу конкретного run_id.

Сделать

    agent_triage/llm/gigachat_client.py:
        LangChain LLM на langchain_gigachat
        единая обертка вызова с логированием по docs/11-llm-logging.md (NDJSON + request/response файлы)
        редактирование секретов/приватных ключей/полных shadow-хешей
    agent_triage/graphrag/retriever.py:
        функции retrieval:
            “host-centric subgraph” по run_id
            “paths user→ip→asn/geo/org”
            выборка “аномалий” из docs/02 (root logins, unusual shells, exec в /tmp, cron suspicious)
        возвращать структурированный контекст для LLM (не дамп всего)
    agent_triage/graphrag/analyst.py:
        prompt-шаблон: требования “evidence-first” (каждый вывод со ссылками на Artifact/Entity/Relation ids)
        выход: Finding[], IOC[], narrative summary

Проверка

    Unit: мок LLM (фиктивные ответы) → пайплайн устойчив.
    Unit: redaction в LLM-логах (секреты не попадают).
    Интеграционный smoke: реальный запуск при наличии GIGACHAT_CREDENTIALS.

Критерий готовности

    Analyst дает объяснимые выводы, привязанные к evidence в KG.

Этап I — Report Agent (RU отчет: md/json + опционально html)

Цель: финальный отчет соответствует docs/06-api-cli.md, язык RU, содержит обязательные секции.

Сделать

    agent_triage/report/render.py:
        report.json: структурный (run/system/users/ssh_logins/enrichment/suspicious/iocs/confidence)
        report.md: читаемый RU, с таблицей findings и ссылками на артефакты
        (опционально) report.html через Jinja2 шаблон в templates/
    Маскирование чувствительного: приватные ключи, токены, shadow-хеши (см. docs/07-security-and-forensics.md).

Проверка

    Unit: генерация отчетов из фикстур state+normalized.
    Smoke: отчет создается даже при частичном успехе (best-effort).

Критерий готовности

    Один образ → triage + KG + GraphRAG вывод → отчет.

5) LangGraph сборка (что именно должен собрать Codex)

В agent_triage/graph.py:

    определить RunState как state-схему
    собрать граф с guards:
        if not linux -> stop
        if no auth logs -> skip log_agent
        if no public IPs -> skip enrichment
    retries/backoff на внешние API и Neo4j
    чекпоинт: после каждого узла сохранять state.json

6) Тестовая стратегия (чтобы “проверка на каждом этапе” была реальной)

    Unit tests (быстрые, без образов):
        парсеры (auth_ssh.py, dpkg/apk best-effort)
        нормализация (entities/relations)
        публичность IP
        LLM logging redaction
    Contract tests:
        normalized/*.json соответствует JSONSchema/Pydantic
    Integration:
        Neo4j в Docker: ingestion идемпотентен
        (опционально) ipinfo с моками
    E2E (ручной/CI optional):
        прогон на небольшом тестовом raw-образе (если появится) или на заранее подготовленной triage-фикстуре (запуск с --skip-collect-triage режимом, который берет уже готовую папку)

7) Секреты/конфиг (что Codex должен заложить)

ENV (см. docs/06-api-cli.md, docs/07-security-and-forensics.md):

    GIGACHAT_CREDENTIALS
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_ISOLATION_MODE=database|container
    IPINFO_TOKEN
    VIRUSTOTAL_API_KEY (только hash lookup, без upload) Правило: секреты не пишем в state/логи, только маскировать.

8) Минимальный “Definition of Done” для MVP

    CLI python -m agent_triage analyze --image X создает run-dir, state.json, normalized/*.json, report/report.md + report.json.
    При включенном Neo4j: KG записан, повторный запуск не плодит дубликаты.
    При включенном LLM: есть triage/<run>/logs/llm/calls.ndjson + (обрезанные) request/response, без утечек секретов.
    Все шаги работают read-only и evidence-first.

9) Что оставить расширением после MVP (не блокирует MVP)

    rpm offline parsing, systemd journal, docker deep scan (лимиты/таймауты)
    векторный слой в Neo4j (hybrid graph+vector)
    REST API (FastAPI) как оболочка над тем же LangGraph
    YARA/ClamAV локально (без запуска файлов из образа)

