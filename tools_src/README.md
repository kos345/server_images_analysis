# 🔍 Forensic Image Triage & Analysis Toolkit

Профессиональный инструмент для триажа и анализа образов дисков в рамках цифровой криминалистики.

## 📋 Описание

Forensic Image Triage & Analysis Toolkit — это модульный Python-инструмент для автоматизированного сбора артефактов из образов дисков Linux-систем, их анализа и генерации отчетов. Проект разработан с учетом возможности интеграции с AI-агентами (LangChain, LangGraph, GigaChat).

## ✨ Основные возможности

- **Обработка образов дисков**: Определение типа образа, конвертация в RAW формат
- **Сбор артефактов**: Автоматический сбор системных артефактов с помощью pytsk3
- **Анализ данных**: Анализ собранных артефактов и генерация HTML-отчетов
- **Обогащение контекста**: Извлечение сущностей (IP, домены, хеши) и обогащение данных
- **Интеграция с Telegram**: Отправка отчетов через Telegram бота
- **LangChain интеграция**: Готовность к использованию с AI-агентами

## 🏗 Структура проекта

```
project_root/
│   requirements.txt
│   README.md
│
├── configs/
│       triage.yaml          # Конфигурация сбора артефактов
│
├── logs/
│       forensic.log         # Логи (создаётся автоматически)
│
├── src/
│   ├── core/
│   │       image_processor.py
│   │
│   ├── triage/
│   │       collector.py
│   │       analyzer.py
│   │       context_enricher.py
│   │
│   ├── integrations/
│   │       telegram_bot.py
│   │       langchain_tools.py
│   │
│   ├── utils/
│   │       logger.py
│   │       filesystem.py
│   │
│   └── main.py
│
└── triage/
    └── (динамически создаваемые директории результатов)
```

## 🚀 Установка

### Требования

- Python 3.11+
- QEMU tools (для конвертации образов)
- pytsk3 (для работы с файловыми системами)

### Установка зависимостей

```bash
# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt
```

### Установка системных зависимостей

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install qemu-utils libtsk-dev
```

**macOS:**
```bash
brew install qemu sleuthkit
```

**Windows:**
- Установить QEMU: https://www.qemu.org/download/#windows
- Установить SleuthKit: https://www.sleuthkit.org/sleuthkit/download.php

## 📖 Использование

### Базовое использование

```bash
# Обработка образа и полный триаж
python -m src.main --image disk.img --triage

# Только обработка образа
python -m src.main --image disk.img

# Триаж с кастомным именем
python -m src.main --image disk.img --triage --name my_analysis
```

### Программное использование

```python
from pathlib import Path
from src.main import ForensicTriageToolkit

# Инициализация
toolkit = ForensicTriageToolkit()

# Запуск триажа
image_path = Path("disk.img")
triage_dir = toolkit.run_triage(image_path, "my_analysis")

print(f"Результаты сохранены в: {triage_dir}")
```

### Использование с LangChain

```python
from langchain.llms import OpenAI
from src.integrations.langchain_tools import LangChainTools

# Инициализация
tools = LangChainTools()
llm = OpenAI(temperature=0)

# Создание агента
agent = tools.create_agent(llm)

# Использование агента
result = agent.run("Проанализируй образ disk.img и собери триаж")
```

## ⚙️ Конфигурация

### Конфигурация триажа

Отредактируйте `configs/triage.yaml` для настройки собираемых артефактов:

```yaml
artifacts:
  system:
    - /etc/os-release
  users:
    - /etc/passwd
  # ... и т.д.
```

### Конфигурация Telegram

Установите переменные окружения:

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

## 📊 Результаты триажа

После выполнения триажа создается директория со следующей структурой:

```
triage/{image_name}_{date}_{uuid}/
├── system/
│   ├── OS.txt
│   ├── services.txt
│   ├── cron.txt
│   ├── apt.txt
│   └── docker.txt
├── users/
│   ├── passwd.txt
│   ├── shadow.txt
│   ├── history_{user}.txt
│   └── history_clear_{user}.txt
├── logs/
│   ├── var.txt
│   ├── www.txt
│   ├── raw/
│   └── clear/
│       └── auth_full.log
├── files/
│   ├── raw/
│   └── iocs.json
├── report.html
└── enriched.json
```

## 🧪 Тестирование

```bash
# Запуск тестов
pytest

# С покрытием
pytest --cov=src --cov-report=html
```

## 📝 Логирование

Все операции логируются в файл `logs/forensic.log` с уровнями:
- DEBUG: Детальная информация
- INFO: Основные операции
- WARNING: Предупреждения
- ERROR: Ошибки
- CRITICAL: Критические ошибки

## 🔧 Разработка

### Форматирование кода

```bash
black src/
```

### Проверка типов

```bash
mypy src/
```

### Линтинг

```bash
flake8 src/
```

## 🐳 Docker

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    qemu-utils \
    libtsk-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "src.main"]
```

## 📄 Лицензия

[Указать лицензию]

## 🤝 Вклад

Приветствуются pull requests и issues!

## 📧 Контакты

[Указать контакты]

## 🙏 Благодарности

- SleuthKit/pytsk3 за инструменты для работы с файловыми системами
- QEMU за инструменты конвертации образов



