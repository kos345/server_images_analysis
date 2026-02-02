# Интерфейсы: CLI (MVP) и REST (опционально)

## 1) CLI (MVP)

### 1.1 Команда

- `python -m agent_triage analyze --image <path> [--profile mvp] [--out ./triage]`

### 1.2 Основные флаги

- `--image`: путь к образу
- `--profile`: `mvp|extended`
- `--out`: базовая директория для результатов
- `--convert-to-raw`: `auto|always|never`
- `--ipinfo-enabled`: `true|false`
- `--neo4j-enabled`: `true|false`
- `--report-format`: `md|json|both`

### 1.3 Вывод

CLI печатает:

- `run_id`
- путь к `triage/<run>/`
- статус: `ok|unsupported_os|error`

## 2) Конфигурация и секреты

### 2.1 Конфиг (YAML/ENV)

Поддержать:

- `AGENT_PROFILE`
- `TRIAGE_OUT_DIR`
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- `IPINFO_TOKEN`
- `GIGACHAT_CREDENTIALS` (или переменная, требуемая `langchain_gigachat`)

### 2.2 Политика хранения

- секреты не пишем в `state.json`
- в отчет не включаем приватные ключи/пароли/полные хеши, если это запрещено политикой

## 3) REST API (опционально)

Если потребуется интеграция “как сервис”, добавляется FastAPI:

- `POST /analyze` — создать job
- `GET /jobs/{id}` — статус
- `GET /jobs/{id}/report` — отчет
- `GET /jobs/{id}/artifacts` — список артефактов

Внутри REST тонко оборачивает тот же LangGraph workflow.

## 4) Формат отчета (MVP)

### 4.1 `report.json` (структурированный)

- `run`: метаданные
- `system`: OS/host/network
- `users`: список + активность
- `ssh_logins`: успешные входы + enrichment
- `suspicious`: findings + evidence
- `iocs`: список IoC
- `confidence`: общая оценка

### 4.2 `report.md` (читаемый)

Разделы:

- Executive summary
- System overview
- Accounts & access
- Services & persistence
- SSH successful logins + IP enrichment
- Suspicious artifacts (таблица)
- IoC list
- Appendix: artifact index

