from typing import Type, Optional
from datetime import datetime, timedelta
from sqlalchemy import delete, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from bot.database.models import TaskStatus
from .base import SQLAlchemyRepository, T
from bot.core.logging import db_logger, log_error_with_metrics, task_cleanup_metrics


class TaskStatusRepository(SQLAlchemyRepository[TaskStatus]):
    def __init__(self, session: AsyncSession, model: Type[T]):
        super().__init__(session, model)

    async def create_task(
        self,
        user_id: int,
        task_name: str,
        task_id: Optional[str] = None
    ) -> TaskStatus:
        """Создать новую запись о задаче."""
        # Сначала проверяем, нет ли уже активной задачи
        existing_task = await self.session.execute(
            select(TaskStatus).where(
                TaskStatus.user_id == user_id,
                TaskStatus.task_name == task_name,
                TaskStatus.status == "running"
            )
        )

        if existing_task.scalar_one_or_none():
            db_logger.warning(
                f"Task {task_name} already running for user {user_id}",
                user_id=user_id,
                task_name=task_name
            )
            raise ValueError(
                f"Task {task_name} already running for user {user_id}")

        task_status = TaskStatus(
            user_id=user_id,
            task_name=task_name,
            task_id=task_id,
            status="running"
        )

        try:
            self.session.add(task_status)
            await self.session.flush()
            db_logger.info(
                f"Task created: {task_name} for user {user_id}",
                user_id=user_id,
                task_name=task_name
            )
            return task_status
        except SQLAlchemyError as e:
            db_logger.error(
                f"Error creating task: {e}",
                user_id=user_id,
                task_name=task_name,
                error=str(e)
            )
            raise

    async def get_active_tasks(self, user_id: int, task_names: Optional[list[str]] = None) -> list[TaskStatus]:
        """Получить активные задачи пользователя."""
        stmt = select(TaskStatus).where(
            TaskStatus.user_id == user_id,
            TaskStatus.status == "running"
        )

        if task_names:
            stmt = stmt.where(TaskStatus.task_name.in_(task_names))

        try:
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            db_logger.error(
                f"Error getting active tasks: {e}",
                user_id=user_id,
                error=str(e)
            )
            return []

    async def has_active_task(self, user_id: int, task_name: str) -> bool:
        """Проверить, есть ли активная задача у пользователя."""
        stmt = select(TaskStatus).where(
            TaskStatus.user_id == user_id,
            TaskStatus.task_name == task_name,
            TaskStatus.status == "running"
        )

        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none() is not None
        except SQLAlchemyError as e:
            db_logger.error(
                f"Error checking active task: {e}",
                user_id=user_id,
                task_name=task_name,
                error=str(e)
            )
            # В случае ошибки считаем, что задача активна (безопасность)
            return True

    async def has_any_active_tasks(self, user_id: int, task_names: list[str]) -> bool:
        """Проверить, есть ли любая из указанных активных задач у пользователя."""
        stmt = select(TaskStatus).where(
            TaskStatus.user_id == user_id,
            TaskStatus.task_name.in_(task_names),
            TaskStatus.status == "running"
        )

        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none() is not None
        except SQLAlchemyError as e:
            db_logger.error(
                f"Error checking any active tasks: {e}",
                user_id=user_id,
                task_names=task_names,
                error=str(e)
            )
            return True  # В случае ошибки считаем, что задача активна

    async def complete_task(
        self,
        user_id: int,
        task_name: str,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> bool:
        """Завершить задачу."""
        stmt = select(TaskStatus).where(
            TaskStatus.user_id == user_id,
            TaskStatus.task_name == task_name,
            TaskStatus.status == "running"
        )

        try:
            result = await self.session.execute(stmt)
            task_status = result.scalar_one_or_none()

            if task_status:
                task_status.status = "completed" if success else "failed"
                task_status.completed_at = datetime.now()
                if error_message:
                    task_status.error_message = error_message

                db_logger.info(
                    f"Task completed: {task_name} for user {user_id}",
                    user_id=user_id,
                    task_name=task_name,
                    success=success
                )
                return True
            else:
                db_logger.warning(
                    f"Task not found for completion: {task_name} for user {user_id}",
                    user_id=user_id,
                    task_name=task_name
                )
                return False

        except SQLAlchemyError as e:
            db_logger.error(
                f"Error completing task: {e}",
                user_id=user_id,
                task_name=task_name,
                error=str(e)
            )
            return False

    async def get_users_with_active_tasks(self, task_names: list[str]) -> list[int]:
        """Получить список user_id пользователей с активными задачами из указанного списка."""
        # Подзапрос для получения пользователей с активными задачами
        subquery = select(TaskStatus.user_id).where(
            TaskStatus.task_name.in_(task_names),
            TaskStatus.status == "running"
        ).distinct()

        try:
            result = await self.session.execute(subquery)
            users_with_active_tasks = [row[0] for row in result.fetchall()]
            return users_with_active_tasks
        except SQLAlchemyError as e:
            db_logger.error(
                f"Error getting users with active tasks: {e}",
                task_names=task_names,
                error=str(e)
            )
            return []

    async def cleanup_old_tasks(self, days_old: int = 7) -> int:
        """Очистить старые завершенные задачи."""
        cutoff_date = datetime.now() - timedelta(days=days_old)

        stmt = select(TaskStatus).where(
            or_(
                TaskStatus.status == "completed",
                TaskStatus.status == "failed"
            ),
            TaskStatus.completed_at < cutoff_date
        )

        try:
            result = await self.session.execute(stmt)
            old_tasks = result.scalars().all()

            for task in old_tasks:
                await self.session.delete(task)

            count = len(old_tasks)
            
            # Обновляем метрики
            task_cleanup_metrics.labels(cleanup_type="old_tasks", status="success").inc(count)
            
            db_logger.info(f"Cleaned up {count} old tasks")
            return count

        except SQLAlchemyError as e:
            db_logger.error(f"Error cleaning up old tasks: {e}", error=str(e))
            # Логируем ошибку с метриками
            log_error_with_metrics(
                error_type="database_error",
                component="task_cleanup",
                severity="error",
                message=f"Error cleaning up old tasks: {e}",
                operation="cleanup_old_tasks",
                days_old=days_old,
                error=str(e)
            )
            task_cleanup_metrics.labels(cleanup_type="old_tasks", status="error").inc()
            return 0

    async def cleanup_hanging_tasks(self, hours_old: int = 2) -> int:
        """Очистить задачи в статусе running, которые работают дольше указанного времени."""
        cutoff_date = datetime.now() - timedelta(hours=hours_old)

        stmt = select(TaskStatus).where(
            TaskStatus.status == "running",
            TaskStatus.created < cutoff_date
        )

        try:
            result = await self.session.execute(stmt)
            hanging_tasks = result.scalars().all()

            for task in hanging_tasks:
                # Обновляем статус на failed вместо удаления для сохранения истории
                task.status = "failed"
                task.completed_at = datetime.now()
                task.error_message = f"Task timeout after {hours_old} hours"
                
                # Логируем каждую зависшую задачу как ошибку
                log_error_with_metrics(
                    error_type="task_timeout",
                    component="task_cleanup",
                    severity="warning",
                    message=f"Task {task.task_name} timed out after {hours_old} hours",
                    user_id=task.user_id,
                    task_name=task.task_name,
                    task_id=task.task_id,
                    hours_old=hours_old,
                    created_at=task.created.isoformat()
                )

            count = len(hanging_tasks)
            
            # Обновляем метрики
            if count > 0:
                task_cleanup_metrics.labels(cleanup_type="hanging_tasks", status="success").inc(count)
                # Также считаем это как предупреждение в общих метриках
                log_error_with_metrics(
                    error_type="hanging_tasks_found",
                    component="task_cleanup",
                    severity="warning",
                    message=f"Found and cleaned {count} hanging tasks (running > {hours_old} hours)",
                    count=count,
                    hours_old=hours_old
                )
            else:
                task_cleanup_metrics.labels(cleanup_type="hanging_tasks", status="success").inc(0)
                
            db_logger.info(f"Marked {count} hanging tasks as failed (running > {hours_old} hours)")
            return count

        except SQLAlchemyError as e:
            db_logger.error(f"Error cleaning up hanging tasks: {e}", error=str(e))
            # Логируем ошибку с метриками
            log_error_with_metrics(
                error_type="database_error",
                component="task_cleanup",
                severity="error",
                message=f"Error cleaning up hanging tasks: {e}",
                operation="cleanup_hanging_tasks",
                hours_old=hours_old,
                error=str(e)
            )
            task_cleanup_metrics.labels(cleanup_type="hanging_tasks", status="error").inc()
            return 0

    async def get_all_running_tasks(self) -> list[TaskStatus]:
        """Получить все задачи в статусе running."""
        stmt = select(TaskStatus).where(
            TaskStatus.status == "running"
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_all_tasks(self, user_id: int) -> None:
        """Удалить все задачи пользователя."""
        stmt = delete(TaskStatus).where(
            TaskStatus.user_id == user_id
        )
        await self.session.execute(stmt)
        db_logger.info(f"Deleted all tasks for user {user_id}")
