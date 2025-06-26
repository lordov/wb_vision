from typing import Optional, Any
from enum import Enum

from bot.database.uow import UnitOfWork
from bot.core.logging import app_logger


class TaskName(Enum):
    """Enum для названий задач."""
    PRE_LOAD_INFO = "pre_load_info"
    START_NOTIF_PIPELINE = "start_notif_pipeline"
    LOAD_STOCKS = "load_stocks"


class TaskControlService:
    """Сервис для контроля выполнения задач."""

    # Определяем зависимости между задачами
    TASK_CONFLICTS = {
        TaskName.START_NOTIF_PIPELINE: [TaskName.PRE_LOAD_INFO, TaskName.START_NOTIF_PIPELINE],
        TaskName.LOAD_STOCKS: [TaskName.LOAD_STOCKS],
    }

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def can_start_task(self, user_id: int, task_name: TaskName) -> bool:
        """
        Проверить, можно ли запустить задачу для пользователя.

        Args:
            user_id: ID пользователя
            task_name: Название задачи

        Returns:
            True если задачу можно запустить, False если нет
        """
        async with self.uow as uow:
            # Проверяем, есть ли уже такая активная задача
            has_same_task = await uow.task_status.has_active_task(
                user_id=user_id,
                task_name=task_name.value
            )

            if has_same_task:
                app_logger.info(
                    f"Task {task_name.value} already running for user {user_id}",
                    user_id=user_id,
                    task_name=task_name.value
                )
                return False

            # Проверяем конфликтующие задачи
            conflicting_tasks = self.TASK_CONFLICTS.get(task_name, [])
            if conflicting_tasks:
                conflicting_task_names = [
                    task.value for task in conflicting_tasks]
                has_conflicting = await uow.task_status.has_any_active_tasks(
                    user_id=user_id,
                    task_names=conflicting_task_names
                )

                if has_conflicting:
                    app_logger.info(
                        f"Task {task_name.value} blocked by conflicting tasks for user {user_id}",
                        user_id=user_id,
                        task_name=task_name.value,
                        conflicting_tasks=conflicting_task_names
                    )
                    return False

            return True

    async def start_task(
        self,
        user_id: int,
        task_name: TaskName,
        task_id: Optional[str] = None
    ) -> bool:
        """
        Зарегистрировать начало выполнения задачи.

        Args:
            user_id: ID пользователя
            task_name: Название задачи
            task_id: ID задачи от брокера (опционально)

        Returns:
            True если задача зарегистрирована, False если нет
        """
        if not await self.can_start_task(user_id, task_name):
            return False

        async with self.uow as uow:
            try:
                await uow.task_status.create_task(
                    user_id=user_id,
                    task_name=task_name.value,
                    task_id=task_id
                )
                await uow.commit()

                app_logger.info(
                    f"Task {task_name.value} started for user {user_id}",
                    user_id=user_id,
                    task_name=task_name.value,
                    task_id=task_id
                )
                return True

            except ValueError as e:
                # Задача уже существует
                await uow.rollback()
                app_logger.info(
                    f"Task {task_name.value} already running for user {user_id}",
                    user_id=user_id,
                    task_name=task_name.value
                )
                return False

            except Exception as e:
                await uow.rollback()
                app_logger.error(
                    f"Failed to start task {task_name.value} for user {user_id}: {e}",
                    user_id=user_id,
                    task_name=task_name.value,
                    error=str(e)
                )
                return False

    async def complete_task(
        self,
        user_id: int,
        task_name: TaskName,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Завершить выполнение задачи.

        Args:
            user_id: ID пользователя
            task_name: Название задачи
            success: Успешно ли завершена задача
            error_message: Сообщение об ошибке (если есть)

        Returns:
            True если задача завершена, False если нет
        """
        async with self.uow as uow:
            try:
                completed = await uow.task_status.complete_task(
                    user_id=user_id,
                    task_name=task_name.value,
                    success=success,
                    error_message=error_message
                )
                await uow.commit()

                if completed:
                    app_logger.info(
                        f"Task {task_name.value} completed for user {user_id}",
                        user_id=user_id,
                        task_name=task_name.value,
                        success=success
                    )

                return completed

            except Exception as e:
                await uow.rollback()
                app_logger.error(
                    f"Failed to complete task {task_name.value} for user {user_id}: {e}",
                    user_id=user_id,
                    task_name=task_name.value,
                    error=str(e)
                )
                return False

    async def get_available_users_for_task(
        self,
        all_user_ids: list[int],
        task_name: TaskName
    ) -> list[int]:
        """
        Получить список пользователей, для которых можно запустить задачу.

        Args:
            all_user_ids: Список всех пользователей
            task_name: Название задачи

        Returns:
            Список user_id пользователей, доступных для задачи
        """
        available_users = []

        for user_id in all_user_ids:
            if await self.can_start_task(user_id, task_name):
                available_users.append(user_id)

        app_logger.info(
            f"Available users for task {task_name.value}: {len(available_users)}/{len(all_user_ids)}",
            task_name=task_name.value,
            available_count=len(available_users),
            total_count=len(all_user_ids)
        )

        return available_users

    async def get_users_with_active_tasks(self, task_names: list[TaskName]) -> list[int]:
        """
        Получить список пользователей с активными задачами.

        Args:
            task_names: Список названий задач

        Returns:
            Список user_id пользователей с активными задачами
        """
        async with self.uow as uow:
            task_name_values = [task.value for task in task_names]
            return await uow.task_status.get_users_with_active_tasks(task_name_values)

    async def cleanup_old_tasks(self, days_old: int = 7) -> int:
        """
        Очистить старые завершенные задачи.

        Args:
            days_old: Количество дней для очистки

        Returns:
            Количество очищенных задач
        """
        async with self.uow as uow:
            try:
                count = await uow.task_status.cleanup_old_tasks(days_old)
                await uow.commit()

                app_logger.info(f"Cleaned up {count} old tasks")
                return count

            except Exception as e:
                await uow.rollback()
                app_logger.error(
                    f"Failed to cleanup old tasks: {e}", error=str(e))
                return 0

    async def get_user_active_tasks(self, user_id: int) -> list[dict[str, Any]]:
        """
        Получить список активных задач пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Список активных задач с информацией
        """
        async with self.uow as uow:
            tasks = await uow.task_status.get_active_tasks(user_id)

            return [
                {
                    "id": task.id,
                    "task_name": task.task_name,
                    "task_id": task.task_id,
                    "started_at": task.created,
                    "status": task.status
                }
                for task in tasks
            ]
