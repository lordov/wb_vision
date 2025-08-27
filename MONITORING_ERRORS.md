# Система мониторинга ошибок

## Обзор

Система автоматического отслеживания и мониторинга ошибок для процессов очистки задач с интеграцией в Prometheus и Grafana.

## Компоненты

### 1. Логгер ошибок с метриками

**Файл:** `bot/core/logging.py`

- `log_error_with_metrics()` - функция для логирования ошибок с отправкой метрик в Prometheus
- `error_counter` - счетчик ошибок по типам, компонентам и серьезности
- `task_cleanup_metrics` - счетчик статистики очистки задач

### 2. Улучшенные методы очистки

**Файл:** `bot/database/repositories/task_status.py`

- `cleanup_hanging_tasks()` - очищает зависшие задачи с логированием каждой ошибки
- `cleanup_old_tasks()` - очищает старые задачи с метриками успеха/ошибок

**Файл:** `bot/services/task_control.py`

- Обертки сервисного уровня с обработкой ошибок и метриками

### 3. Автоматические задачи

**Файл:** `broker.py`

- `cleanup_hanging_tasks` - выполняется каждые 30 минут
- `cleanup_old_tasks` - выполняется ежедневно в 2:00

## Метрики Prometheus

### application_errors_total
Общий счетчик ошибок приложения с лейблами:
- `error_type`: тип ошибки (task_timeout, database_error, hanging_tasks_found, etc.)
- `component`: компонент (task_cleanup, task_control_service, etc.)
- `severity`: серьезность (error, warning, critical)

### task_cleanup_total
Счетчик операций очистки задач с лейблами:
- `cleanup_type`: тип очистки (old_tasks, hanging_tasks)
- `status`: результат (success, error)

## Алерты Prometheus

### Группа: application_errors

1. **HighCleanupErrorRate** - высокая частота ошибок очистки (> 0.1/сек в течение 2 мин)
2. **CriticalCleanupErrors** - критические ошибки очистки
3. **HangingTasksDetected** - обнаружены зависшие задачи
4. **FrequentTaskTimeouts** - частые таймауты задач (> 0.5/сек в течение 5 мин)
5. **DatabaseErrors** - ошибки базы данных

## Grafana Dashboard

**Файл:** `monitoring/grafana/dashboards/errors-overview.json`

### Панели:
1. **Общая частота ошибок** - сводная статистика ошибок в секунду
2. **Частота ошибок по типам** - временной ряд по типам ошибок
3. **Сводка ошибок** - таблица с детализацией по типам
4. **Статистика очистки задач** - успешные/неуспешные операции очистки
5. **Зависшие задачи за час** - количество обнаруженных зависших задач
6. **Ошибки БД за час** - количество ошибок базы данных

## Типы отслеживаемых ошибок

### task_timeout
- **Описание:** Задача работает дольше 2 часов
- **Серьезность:** warning
- **Компонент:** task_cleanup
- **Действие:** Задача помечается как failed с сообщением о таймауте

### database_error
- **Описание:** Ошибки при работе с базой данных
- **Серьезность:** error
- **Компонент:** task_cleanup
- **Действие:** Логирование ошибки, возврат 0 для количества обработанных задач

### hanging_tasks_found
- **Описание:** Обнаружены зависшие задачи
- **Серьезность:** warning
- **Компонент:** task_cleanup
- **Действие:** Сводная статистика по найденным зависшим задачам

### cleanup_service_error
- **Описание:** Ошибки на уровне сервиса задач
- **Серьезность:** error
- **Компонент:** task_control_service
- **Действие:** Повторное выбрасывание исключения после логирования

## Использование

### Логирование ошибки с метриками

```python
from bot.core.logging import log_error_with_metrics

log_error_with_metrics(
    error_type="database_error",
    component="task_cleanup",
    severity="error",
    message="Failed to connect to database",
    operation="cleanup_old_tasks",
    error=str(exception)
)
```

### Просмотр метрик

1. **Prometheus:** http://localhost:9090/graph
2. **Grafana:** http://localhost:3000 (admin/admin)
   - Dashboard: "Ошибки приложения"

### Примеры запросов Prometheus

```promql
# Частота ошибок очистки задач
rate(application_errors_total{component="task_cleanup"}[5m])

# Количество зависших задач за час
sum(increase(application_errors_total{error_type="hanging_tasks_found"}[1h]))

# Статистика успешных операций очистки
rate(task_cleanup_total{status="success"}[5m])
```

## Настройка алертов

Алерты настраиваются в файле `monitoring/prometheus/alert_rules.yml` и автоматически загружаются в Prometheus при запуске через docker-compose.

Для получения уведомлений необходимо настроить Alertmanager (не включен в текущую конфигурацию).
