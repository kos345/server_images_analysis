# Triage prompts (каркас)

Эта директория содержит **прикладные промпты LLM** для этапа `triage_summaries` (и родственных шагов), упомянутые в ТЗ заказчика (`system_services`, `cron`, `apt_summary`, и т.д.).

## Принципы

- **Evidence-first**: любые выводы должны опираться на входной текст/артефакты.
- **RU-only**: текстовые поля и summary — на русском языке.
- **Не хардкодить пайплайн**: промпты описывают *задачу анализа* и *формат ответа*, а не “как именно” собирать данные.
- **Стабильный формат**: по умолчанию промпт просит вернуть:
  - структурированный JSON (для дальнейшей загрузки в Neo4j),
  - и краткий markdown summary (для `triage/<run>/summaries/*.md`).

## Где используется

Реестр ключей и загрузка промптов: `prompts/triage_prompts.py`.

## Ключи (MVP)

- `system_services` → `system_services.md`
- `cron` → `cron.md`
- `apt_summary` → `apt_summary.md`
- `log_files_summary` → `log_files_summary.md`
- `root_files_summary` → `root_files_summary.md`
- `history_summary` → `history_summary.md`
- `files_wl` → `files_wl.md`
- `home_files_summary` → `home_files_summary.md`

