Ты анализируешь список файлов и директорий в корне файловой системы (`files/root_dir.txt`).

## Цель

Сформировать список **нестандартных (не системных)** файлов/директорий и отметить потенциально подозрительные (persistence/tools/payload).

## Правила

- Опирайся только на входной список.
- Не требуются абсолютные доказательства “вредоносности”; цель — triage.
- Язык: русский.

## Вход

`root_dir_listing` — список путей/имен из `files/root_dir.txt`.

## Выход (строгий JSON + markdown)

JSON:

```json
{
  "nonstandard_items": [
    {
      "path": "как во входе",
      "type_guess": "file|dir|unknown",
      "suspicion": "low|medium|high",
      "reasons": ["..."],
      "evidence": {"type": "artifact", "path": "files/root_dir.txt"}
    }
  ],
  "notes": ["ограничения/нехватка данных"]
}
```

Markdown summary: 5–20 строк, что выделено и почему.

