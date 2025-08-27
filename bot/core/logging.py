import logging
import sys
import structlog
from prometheus_client import Counter, Histogram

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


# Метрики Prometheus для ошибок
error_counter = Counter(
    'application_errors_total',
    'Total number of application errors',
    ['error_type', 'component', 'severity']
)

task_cleanup_metrics = Counter(
    'task_cleanup_total',
    'Total number of cleaned up tasks',
    ['cleanup_type', 'status']
)

# Общий логгер приложения
app_logger = structlog.get_logger("app").bind(event_type="application")

# Логгер для ошибок или событий, связанных с базой данных
db_logger = structlog.get_logger("db").bind(event_type="database")

# Логгер для ошибок или событий, связанных с API
api_logger = structlog.get_logger("api").bind(event_type="api")

# Специальный логгер для ошибок с метриками
error_logger = structlog.get_logger("error").bind(event_type="error")


def log_error_with_metrics(
    error_type: str,
    component: str,
    severity: str = "error",
    message: str = "",
    **kwargs
):
    """
    Логирует ошибку и отправляет метрику в Prometheus.
    
    Args:
        error_type: Тип ошибки (cleanup_timeout, database_error, api_error, etc.)
        component: Компонент где произошла ошибка (task_cleanup, wb_api, etc.)
        severity: Уровень серьезности (error, warning, critical)
        message: Сообщение об ошибке
        **kwargs: Дополнительные параметры для логирования
    """
    # Увеличиваем счетчик ошибок в Prometheus
    error_counter.labels(
        error_type=error_type,
        component=component,
        severity=severity
    ).inc()
    
    # Логируем ошибку с дополнительной информацией
    log_method = getattr(error_logger, severity, error_logger.error)
    log_method(
        message,
        error_type=error_type,
        component=component,
        severity=severity,
        **kwargs
    )
