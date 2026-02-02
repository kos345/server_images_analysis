# Workflow triage (образы, OS-detection, сбор артефактов, логи, enrichment)

## 0) Входы/выходы run

### Вход

- `image_path`: путь к образу диска
- `profile`: `mvp|extended`
- `out_dir`: базовая директория (`./triage` по умолчанию)
- `ipinfo_token`: секрет для API (bulk)
- `virustotal_api_key`: ключ VT (lookup по SHA256; опционально)
- `neo4j_uri`, `neo4j_user`, `neo4j_password`

### Выход

В `triage/<image>_<YYYY-MM-DD>_<uuid>/`:

- `state.json` — итоговый state
- `raw/` — “сырые” артефакты (копии ключевых файлов, выгрузки)
- `normalized/` — сущности/связи (JSON)
- `kg/` — статистика/логи ingestion
- `report/` — `report.md`, `report.json`
- `logs/` — логи выполнения (audit trail)

Дополнительно (как в ТЗ заказчика):

- `system/OS.txt`
- `users/passwd.txt`, `users/shadow.txt`, `users/history_{user}.txt`, `users/history_clear_{user}.txt`
- `files/home.txt`, `files/root.txt`, `files/root_dir.txt`
- `system/services.txt`, `system/cron.txt`, `system/apt.txt`, `system/docker.txt`
- `logs/var.txt`, `logs/www.txt`, `logs/raw/var`, `logs/raw/www`, `logs/clear/auth_full.log`, `logs/clear/success_auth.log`, `logs/clear/success_auth_IP.json`
- `files/iocs_full.json`, `files/iocs_clear.json`, `files/iocs_vt.json`
- `summaries/*.md` (LLM summaries)

## 1) Ingest: форматы образов и конверсия в raw

### 1.1 Поддерживаемые форматы (MVP)

- `raw`
- `qcow2`

Расширение (не MVP): `vmdk`, `vdi` (через `qemu-img`).

### 1.2 Конверсия (если нужно)

- инструмент: `qemu-img convert -O raw <input> <output>`
- сохраняем:
  - `input_path`, `output_path`
  - `sha256(input)`, `sha256(output)`
  - версию `qemu-img`

## 2) OS detection (только Linux)

### 2.1 Способы детекта

В порядке предпочтения:

1) mount + чтение `/etc/os-release`  
2) `ls`/поиск `vmlinuz`, `init`, `systemd`, `/bin/bash`  
3) fallback: сигнатуры файловых систем/разделов (best-effort)

### 2.2 Stop condition

Если family != `linux`:

- завершить run со статусом `unsupported_os`,
- сформировать короткий отчет (что обнаружено, почему остановлено).

## 3) Доступ к файловой системе (read-only)

### 3.1 Стратегии монтирования

MVP опирается на **pytsk3** для чтения файловых систем/извлечения файлов из образа (без boot, read-only по смыслу).

Расширение (опционально):

- libguestfs/guestmount
- nbd (`qemu-nbd --read-only`) + mount разделов

### 3.2 Требования read-only

- любая команда mount с `-o ro`
- запрет модификаций и записи в image
- запись audit trail

## 4) Сбор артефактов (Filesystem Triage)

Ниже — минимальный список (MVP). Каждый пункт:

- сохраняет raw копию/выгрузку,
- нормализует в сущности/связи,
- добавляет findings при подозрительности.

### 4.1 OS/Host

- `/etc/os-release`, `/etc/issue`
- `/etc/hostname`
- `/proc/version` (если доступно через image), иначе `uname` нельзя

### 4.2 Network

- `/etc/hosts`, `/etc/resolv.conf`
- distro-specific:
  - Debian/Ubuntu: `/etc/network/interfaces`, `/etc/netplan/*.yaml`
  - RHEL/CentOS: `/etc/sysconfig/network-scripts/ifcfg-*`
  - systemd: `/etc/systemd/network/*.network`
- cloud-init: `/etc/cloud/cloud.cfg*`, `/var/lib/cloud/`

### 4.3 Users/Groups/Auth

- `/etc/passwd`, `/etc/group`
- `/etc/shadow` (если доступно) — только хеши (не пытаться “ломать” в MVP)
- `/etc/sudoers`, `/etc/sudoers.d/*`
- SSH:
  - `/etc/ssh/sshd_config`
  - `/etc/ssh/ssh_host_*` (fingerprints, без приватных ключей в отчет)
  - `~/.ssh/authorized_keys` всех пользователей

### 4.4 Shell histories

По пользователям:

- `~/.bash_history`
- `~/.zsh_history`
- `~/.ash_history` (alpine)

Нормализация:

- `CommandHistoryEntry {user, shell, command, ts?}`  
Если timestamp недоступен — `ts=null`.

### 4.5 Services and persistence

- systemd:
  - `/etc/systemd/system/*.service`
  - `/lib/systemd/system/*.service` (для сравнения)
  - `/etc/systemd/system/*.timer`
- init.d: `/etc/init.d/*`
- автозагрузка:
  - `rc.local` (если есть)

Нормализация:

- `Service`, `Finding` (например, unit в `/etc/systemd/system` с ExecStart на `/tmp/...`).

### 4.6 Scheduler (cron)

- `/etc/crontab`
- `/etc/cron.*/*`
- `/var/spool/cron/*` или `/var/spool/cron/crontabs/*`

### 4.7 Packages

Дистрибутивно:

- Debian/Ubuntu: `/var/lib/dpkg/status`
- RHEL: rpm db (в MVP можно best-effort: `rpm` parsing сложно офлайн)
- Alpine: `/lib/apk/db/installed`

MVP: качественно поддержать `dpkg` и `apk`.

### 4.8 Web servers / app stacks (MVP: presence & config)

- nginx: `/etc/nginx/`, логи в `/var/log/nginx/` (если есть)
- apache: `/etc/apache2/` или `/etc/httpd/`
- php-fpm: `/etc/php/*/fpm/`
- node apps: поиск `package.json` в `/var/www`, `/opt`, `/srv`

### 4.9 Docker

- `/var/lib/docker/` (важно: может быть огромный)
- минимальный MVP:
  - `/etc/docker/daemon.json`
  - `/var/lib/docker/containers/*/*-json.log` (опционально)
  - `docker-compose.yml` (поиск в типовых директориях)

В MVP важно предусмотреть лимиты/таймауты.

### 4.10 Non-system files/dirs (heuristics)

Правила (MVP):

- пути: `/tmp`, `/var/tmp`, `/dev/shm`, `/run`, `/var/run`
- скрытые директории в home (`~/.<random>`)
- бинарники/скрипты в необычных местах (`/etc/…`, `/usr/local/bin/…` без пакета)
- файлы с execute-bit в webroot

Нормализация:

- `File` + `Finding` с evidence.

## 5) Анализ логов (MVP: успешные SSH logins)

### 5.1 Источники логов

- Debian/Ubuntu: `/var/log/auth.log` (+ rotated `auth.log.*`)
- RHEL/CentOS: `/var/log/secure` (+ rotated)

### 5.2 Фильтр “только успешные”

MVP-паттерны:

- `Accepted password for <user> from <ip> port <port> ssh2`
- `Accepted publickey for <user> from <ip> port <port> ssh2`

Сохраняем:

- ts (из syslog timestamp + год восстановить по эвристике/mtime файла),
- user,
- ip,
- port,
- auth_method (password/publickey/other),
- raw_line_hash (чтобы не тащить строку целиком в KG).

### 5.3 Корреляция с triage

Log Agent использует:

- список пользователей из `/etc/passwd`,
- ssh конфиг (например, PermitRootLogin),
- known keys (если publickey).

## 6) Выделение публичных IP + ipinfo bulk

### 6.1 Публичность IP

- исключить RFC1918, localhost, link-local, CGNAT, multicast и т.п.
- поддержать IPv4 (MVP), IPv6 (опционально).

### 6.2 Bulk запрос

- группируем IP батчами (лимит зависит от тарифа ipinfo)
- кешируем по IP (на диск) чтобы повторные run не тратили квоту

Сохраняем raw ответы (обрезая лишнее) + нормализацию в сущности `ASN/Geo/Org/PrivacyFlag`.

## 7) Проверка “нестандартных файлов” на malware (опционально в MVP)

Режимы (MVP):

- `off`
- `hash-only` (считать sha256/sha1/md5 и формировать IOC JSON)
- `vt-lookup` (если есть `VIRUSTOTAL_API_KEY`): делать **lookup по SHA256** и добавлять поле `VT` в `files/iocs_vt.json` (без загрузки файлов).

Примечание: VT шаг включается флагом и выполняется только при наличии ключа.

## 8) Контракт нормализованных данных (MVP)

В `normalized/`:

- `entities.json` — список сущностей
- `relations.json` — список связей
- `findings.json` — список находок
- `iocs.json` — список IoC

Каждая запись содержит:

- `id`, `type/label`
- `properties`
- `provenance`: `{run_id, artifact_path, artifact_sha256, offset?, line?}`

## 9) Производительность и полный обход ФС (MVP)

Входные ожидания:

- типичный размер образа: **до ~20GB**
- бюджет времени на анализ: **до ~1 часа**

Политика file-walk:

- **полный рекурсивный обход ФС допустим**, но с балансом (MVP).

### 9.1 Исключения “тяжелых/стандартных” каталогов по умолчанию

По умолчанию исключаем из глубокого обхода (но не запрещаем точечные проверки):

- `/var/lib/docker` (контейнерные слои/образы — очень объемно)
- `/var/log` (кроме `auth.log`/`secure` для MVP)
- `/var/cache`, `/var/tmp` (можно оставить эвристический проход)
- `/usr/share`, `/lib/modules` (обычно шум)

### 9.2 Условное “углубление” в исключенные каталоги

Если triage обнаруживает признаки подозрительности, агент **должен** уметь углубиться в исключенный каталог, например:

- найден unit/cron, указывающий на путь внутри исключенного дерева,
- найден исполняемый файл/скрипт с подозрительным именем/правами/временем,
- есть ссылки/строки конфигов на конкретный подпуть.

Реализация: двухфазный подход

1) быстрый “скан метаданных” (names/permissions/mtime/size, без чтения содержимого) для исключенных деревьев,
2) точечный deep scan для конкретных подпутей при срабатывании эвристик.

### 9.3 Политика хеширования (MVP)

Хешируем **не все файлы**, а только:

- исполняемые (`+x`) и/или ELF/скрипты,
- файлы в “опасных” директориях (`/tmp`, `/dev/shm`, `~/.ssh`, cron paths, webroot),
- файлы, отмеченные эвристиками как подозрительные.

Большие файлы (например, >N MB) — по конфигу: либо пропускать, либо считать частичный хеш (опционально), но в MVP можно пропускать.

## 10) LLM summaries (как в ТЗ)

В MVP допускаются LLM-вызовы (GigaChat) для формирования markdown-summary файлов:

- `summaries/services_summary.md` из `system/services.txt` (prompt: `system_services`)
- `summaries/cron_summary.md` из `system/cron.txt` (prompt: `cron`)
- `summaries/apt_summary.md` из `system/apt.txt` (prompt: `apt_summary`)
- `summaries/log_files_summary.md` из `logs/var.txt` и `logs/www.txt` (prompt: `log_files_summary`)
- `summaries/root_files_summary.md` из `files/root_dir.txt` (prompt: `root_files_summary`)
- `summaries/history_{user}_summary.md` из `users/history_clear_{user}.txt` (prompt: `history_summary`)
- `summaries/home_files_summary.md` из extracted files list (в ТЗ указан prompt `history_summary`, но в реализации лучше отдельный prompt под файлы)

Требование: **логировать запросы и ответы LLM** (см. `docs/07-security-and-forensics.md`).

