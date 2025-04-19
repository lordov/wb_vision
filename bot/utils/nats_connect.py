import nats
import logging

from nats.aio.client import Client
from nats.js import JetStreamContext
from nats.aio.errors import ErrTimeout, ErrNoServers


logger = logging.getLogger('app_error_logger')


async def connect_to_nats(servers: list[str]) -> tuple[Client, JetStreamContext]:
    """
    Connect to NATS servers and return a tuple of a Client object and a JetStreamContext object.

    :param servers: List of NATS servers to connect to
    :return: A tuple of a Client object and a JetStreamContext object
    """
    try:
        nc: Client = await nats.connect(servers)
        js: JetStreamContext = nc.jetstream()
    except (ErrTimeout, ErrNoServers) as e:
        logger.error(e)
    return nc, js
