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
- `--vt-enabled`: `true|false` (lookup по SHA256, без upload)
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
- `VIRUSTOTAL_API_KEY`
- `GIGACHAT_CREDENTIALS` (или переменная, требуемая `langchain_gigachat`)

Параметры “кейс/изоляция”:

- `CASE_NAME` (опционально; по умолчанию вычисляется как `case_<image_file_name>` с sanitization)
- `NEO4J_ISOLATION_MODE`: `database|container`
  - `database`: создаем/выбираем БД `CASE_NAME` (если доступно)
  - `container`: один кейс = один neo4j контейнер/инстанс (бесплатный режим, если multiple databases недоступны)

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

Требования:

- язык: **русский (RU)**
- форма: **свободная**, но должна включать обязательное содержание (будет уточнено отдельно)

## 4.3 `report.html` (MVP, как в ТЗ)

В MVP основной человекочитаемый отчет — **HTML**, генерируется через **Jinja2** шаблон из `templates/` в корне проекта.

Отчет должен включать (минимум, как в ТЗ заказчика):

- **Общие сведения о системе**:
  - версия ОС (`system/OS.txt`)
  - пользователи + shadow (`users/passwd.txt`, `users/shadow.txt`) — с маскированием
  - нестандартные сервисы (`summaries/services_summary.md`)
  - задачи планировщика (`summaries/cron_summary.md`)
  - подозрительные пакеты (`summaries/apt_summary.md`)
  - веб-сервера/ПО (`summaries/log_files_summary.md`)
  - docker (`system/docker.txt`)
- **Информация о файлах**:
  - нестандартные файлы/директории в `/` (`summaries/root_files_summary.md`)
  - структура `/home` (`files/home.txt`)
  - структура `/root` (`files/root.txt`)
  - нестандартные файлы в home (`summaries/home_files_summary.md`)
- **Подключения к системе**:
  - успешные SSH входы (`logs/clear/success_auth.log`)
  - обогащение IP (`logs/clear/success_auth_IP.json`)
- **Активность пользователей**:
  - очищенная история команд (`users/history_clear_{user}.txt`)
  - summary по командам (`summaries/history_{user}_summary.md`)
- **Индикаторы компрометации (IoC)**:
  - IP из истории (`users/history_clear_{user}_IP.json`)
  - хостовые артефакты (`files/iocs_full.json` и/или `files/iocs_clear.json`, `files/iocs_vt.json` при включенном VT)

## 4.4 Telegram summary (MVP, как в ТЗ)

Генерируется краткое текстовое резюме для Telegram + отправка HTML/IoC файлов (если включено).

Рекомендуемые разделы (для `report.md`/JSON как baseline, если будут использоваться):

- Executive summary
- System overview
- Accounts & access
- Services & persistence
- SSH successful logins + IP enrichment
- Suspicious artifacts (таблица)
- IoC list
- Appendix: artifact index

