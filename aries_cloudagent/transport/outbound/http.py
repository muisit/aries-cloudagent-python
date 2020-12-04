"""Http outbound transport."""

import logging
from typing import Union

from aiohttp import ClientSession, DummyCookieJar, TCPConnector

from ...config.injection_context import InjectionContext

from ..stats import StatsTracer

from .base import BaseOutboundTransport, OutboundTransportError

import traceback

class HttpTransport(BaseOutboundTransport):
    """Http outbound transport class."""

    schemes = ("http", "https")

    def __init__(self) -> None:
        """Initialize an `HttpTransport` instance."""
        super().__init__()
        self.client_session: ClientSession = None
        self.connector: TCPConnector = None
        self.logger = logging.getLogger(__name__)

    async def start(self):
        """Start the transport."""
        session_args = {}
        self.connector = TCPConnector(limit=200, limit_per_host=50)
        if self.collector:
            session_args["trace_configs"] = [
                StatsTracer(self.collector, "outbound-http:")
            ]
        session_args["cookie_jar"] = DummyCookieJar()
        session_args["connector"] = self.connector
        self.client_session = ClientSession(**session_args)
        return self

    async def stop(self):
        """Stop the transport."""
        await self.client_session.close()
        self.client_session = None

    async def handle_message(
        self, context: InjectionContext, payload: Union[str, bytes], endpoint: str
    ):
        """
        Handle message from queue.

        Args:
            context: the context that produced the message
            payload: message payload in string or byte format
            endpoint: URI endpoint for delivery
        """
        if not endpoint:
            raise OutboundTransportError("No endpoint provided")
        headers = {}
        if isinstance(payload, bytes):
            headers["Content-Type"] = "application/ssi-agent-wire"
        else:
            headers["Content-Type"] = "application/json"
        self.logger.debug(
            "Posting to %s; Data: %s; Headers: %s", endpoint, payload, headers
        )
        try:
            response = await self.client_session.post(
                endpoint, data=payload, headers=headers
            )

            if response:
                self.logger.debug("response status is " + str(response.status))
                if response.status < 200 or response.status > 299:
                    raise OutboundTransportError(
                        (
                            f"Unexpected response status {response.status}, "
                            f"caused by: {response.reason}"
                        )
                    )
            else:
                raise OutboundTransportError(
                    (
                        f"Unexpected empty response, "
                        f"caused by unknown error"
                    )
                )
        except:
            self.logger.debug("caught exception on client_session POST")
            traceback.print_exc()
