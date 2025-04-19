from ..models import User
from .base import SQLAlchemyRepository


class UserRepository(SQLAlchemyRepository[User]):
    model = User
