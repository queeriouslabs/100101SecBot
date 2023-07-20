import asyncio
from unittest.mock import (
    patch,
    AsyncMock
)
import pytest


@pytest.mark.asyncio
async def test_example():
    mocked = AsyncMock()

    loop = asyncio.get_event_loop()
    task = loop.create_task(mocked())
    assert mocked.called
    # mocked.assert_awaited()
