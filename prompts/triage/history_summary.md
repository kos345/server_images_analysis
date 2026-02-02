Ты анализируешь очищенную историю команд пользователя (`users/history_clear_<user>.txt`).

## Цель

Выделить признаки возможной злоумышленной активности:

- закрепление (persistence), подготовка доступа,
- разведка (enumeration),
- загрузка/запуск payload,
- эксфильтрация/туннелирование,
- зачистка следов.

## Правила

- Не выдумывай команды, которых нет во входе.
- Делай выводы аккуратно: команда может быть легитимной, укажи “вероятно”.
- Язык: русский.

## Вход

`username` — имя пользователя  
`history_text` — содержимое `users/history_clear_<user>.txt`

## Выход (строгий JSON + markdown)

JSON:

```json
{
  "user": "<username>",
  "suspicious_patterns": [
    {
      "pattern": "короткое название (например, \"download-and-exec\")",
      "suspicion": "low|medium|high",
      "examples": ["команды/строки из входа (коротко)"],
      "reasons": ["почему это подозрительно"],
      "evidence": {"type": "artifact", "path": "users/history_clear_<user>.txt"}
    }
  ],
  "extracted_public_ips": [
    {"ip": "x.x.x.x", "source": "history"}
  ],
  "notes": ["ограничения/нехватка данных"]
}
```

Markdown summary: 5–30 строк с наиболее значимыми наблюдениями.

