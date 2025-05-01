from taskiq import TaskiqEvents
from taskiq_nats import NatsBroker
from bot.core.config import settings

broker = NatsBroker(settings.nats.url)
