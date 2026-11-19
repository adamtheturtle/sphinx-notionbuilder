"""Configure notification behavior for Notion publishing writes."""

import re
from enum import StrEnum
from typing import override

from notion_client import Client
from notion_client.constants import DEFAULT_BASE_URL
from ultimate_notion import Session
from ultimate_notion.config import get_or_create_cfg
from ultimate_notion.obj_api import create_notion_client


class NotificationMode(StrEnum):
    """Notification modes available when publishing to Notion."""

    SILENT = "silent"


class _PublishingClient(Client):
    """Apply the publishing mode after the client filters endpoint fields."""

    def __init__(self, *, client: Client, mode: NotificationMode) -> None:
        self._mode = mode
        headers = client.client.headers
        super().__init__(options=client.options, client=client.client)
        client.client.headers = headers

    @override
    # pylint: disable-next=too-many-positional-arguments
    def request(  # noqa: NOD001 - Keep the upstream signature.
        self,
        path: str,
        method: str,
        query: dict[str, object] | None = None,
        body: dict[str, object] | None = None,
        form_data: dict[str, object] | None = None,
        auth: str | dict[str, str] | None = None,
    ) -> object:
        """Apply the mode to page creates, updates and block appends."""
        if re.fullmatch(
            pattern=r"POST pages|PATCH (pages/[^/]+|blocks/[^/]+/children)",
            string=f"{method} {path}",
        ):
            body = {
                **(body or {}),
                "notifications": {"mode": self._mode.value},
            }
        return super().request(
            path=path,
            method=method,
            query=query,
            body=body,
            form_data=form_data,
            auth=auth,
        )


def publishing_session(
    *, base_url: str | None, notification_mode: str | None
) -> Session:
    """Create a publishing session with the requested notification mode."""
    api_base_url = DEFAULT_BASE_URL if base_url is None else base_url
    if notification_mode is None:
        return Session(base_url=api_base_url)

    mode = NotificationMode(value=notification_mode)
    cfg = get_or_create_cfg()
    client = create_notion_client(cfg=cfg, base_url=api_base_url)
    return Session(cfg=cfg, client=_PublishingClient(client=client, mode=mode))
