import logging
import sys
import structlog

# Можно переключать режим логирования через переменные окружения, если хочешь
DEBUG = True  # В проде — False, тогда лог будет в JSON


def setup_logging():
    """Настройка базового логгирования через structlog."""
    # Настройка стандартного логгера Python
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    # Список процессоров логирования
    processors = [
        structlog.processors.TimeStamper(fmt="iso"),  # Время в ISO формате
        # Добавляет уровень (info, error и т.д.)
        structlog.stdlib.add_log_level,
        # Добавляет имя логгера ("app", "db" и т.п.)
        structlog.stdlib.add_logger_name,
        structlog.processors.StackInfoRenderer(),     # Отображение стека при ошибках
        structlog.processors.format_exc_info,         # Подробности исключений
        structlog.processors.UnicodeDecoder(),        # Обработка Unicode
        structlog.dev.ConsoleRenderer() if DEBUG else structlog.processors.JSONRenderer(),
    ]

    # Конфигурация structlog
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


# Общий логгер приложения
app_logger = structlog.get_logger("app").bind(event_type="application")

# Логгер для ошибок или событий, связанных с базой данных
db_logger = structlog.get_logger("db").bind(event_type="database")

# Логгер для ошибок или событий, связанных с API
api_logger = structlog.get_logger("api").bind(event_type="api")
