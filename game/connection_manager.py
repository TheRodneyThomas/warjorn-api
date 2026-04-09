# Copyright (c) 2026 R7L LLC. All Rights Reserved.
#
# PROPRIETARY AND CONFIDENTIAL
#
# This software and its source code are the exclusive property of R7L LLC
# and are protected by copyright law and international treaties.
#
# Unauthorized copying, distribution, modification, public display, or
# public performance of this software, in whole or in part, is strictly
# prohibited without the prior written consent of R7L LLC.
#
# For licensing inquiries, contact: legal@r7l.us

import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, username: str, websocket: WebSocket):
        # If the player is already connected, close the old connection
        if username in self.active:
            await self.active[username].close(code=1008)
            logger.warning("Replaced existing connection for: %s", username)
        self.active[username] = websocket

    def disconnect(self, username: str):
        self.active.pop(username, None)

    async def send(self, username: str, message: dict):
        websocket = self.active.get(username)
        if websocket:
            await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for websocket in list(self.active.values()):
            await websocket.send_json(message)
