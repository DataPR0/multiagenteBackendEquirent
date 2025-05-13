from fastapi import WebSocket
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel
from enum import Enum
from app.config import settings
from app.utilities.logger import logger
from app.utilities.pubsub import RedisPubSubManager
from app.models.websockets import (
    Notification,
    ChatWebSocketResponseType,
    ChatWebSocketResponse,
    MessageData
)

import json
import asyncio


class WebSocketType(str, Enum):
    """
    Enum class for WebSocket types.

    Attributes:
        NOTIFICATION (str): Notification WebSocket type.
        CONVERSATION (str): Conversation WebSocket type.
    """
    NOTIFICATIONS = "notifications"
    CONVERSATION = "conversation"


class WebSocketConfig(BaseModel):
    """
    WebSocket configuration model.

    Attributes:
        ws_type (Literal[WebSocketType.NOTIFICATIONS, WebSocketType.CONVERSATION]): WebSocket type.
        user_id (int): User identifier.
        conversation_id (Optional[int]): Conversation identifier.
    """
    ws_type: Literal[
        WebSocketType.NOTIFICATIONS,
        WebSocketType.CONVERSATION
    ]
    user_id: int
    conversation_id: Optional[int] = None


class WebSocketManager:
    def __init__(self):
        """
        Initializes the WebSocketManager.

        Attributes:
            notifications (dict): A dictionary to store WebSocket notifications.
            conversations (dict): A dictionary to store WebSocket chats.
            lock (asyncio.Lock): A lock to prevent race conditions when modifying shared resources.
        """
        # notifications: {user_id: [WebSocket, WebSocket, ...]}
        self.notifications: Dict[int, List[WebSocket]] = {}
        # conversations: {conversation_id: {user_id: [WebSocket, WebSocket, ...]}}
        self.conversations: Dict[int, Dict[int, List[WebSocket]]] = {}
        self.pubsub_client = RedisPubSubManager(settings.redis_host, 6379)
        self.lock = asyncio.Lock()  # Add a lock to protect shared resources

    async def add_connection(self, ws_config: WebSocketConfig, websocket: WebSocket) -> None:
        """
        Adds a WebSocket connection to the WebSocketManager.

        Args:
            ws_config (WebSocketConfig): WebSocket configuration.
            websocket (WebSocket): WebSocket connection object.
        """
        async with self.lock:
            if ws_config.ws_type == WebSocketType.NOTIFICATIONS:
                if ws_config.user_id not in self.notifications:
                    self.notifications[ws_config.user_id] = []
                    pubsub_subscriber = await self.pubsub_client.subscribe(f"user_{ws_config.user_id}")
                    asyncio.create_task(
                        self._pubsub_data_reader(pubsub_subscriber),
                        name=f"user_{ws_config.user_id}"
                    )
                    logger.info(f"Subscribed to user_{ws_config.user_id} redis channel")
                self.notifications[ws_config.user_id].append(websocket)
            elif ws_config.ws_type == WebSocketType.CONVERSATION:
                if ws_config.conversation_id not in self.conversations:
                    self.conversations[ws_config.conversation_id] = {}
                    pubsub_subscriber = await self.pubsub_client.subscribe(f"conversation_{ws_config.conversation_id}")
                    asyncio.create_task(
                        self._pubsub_data_reader(pubsub_subscriber),
                        name=f"conversation_{ws_config.conversation_id}"
                    )
                    logger.info(f"Subscribed to conversation_{ws_config.conversation_id} redis channel")
                if ws_config.user_id not in self.conversations[ws_config.conversation_id]:
                    self.conversations[ws_config.conversation_id][ws_config.user_id] = []
                self.conversations[ws_config.conversation_id][ws_config.user_id].append(websocket)
            logger.info(f"WebSocket connection added: {ws_config}")
        
    async def send_notification(self, user_id: int, notification: Notification) -> None:
        """
        Sends a notification to a user.

        Args:
            user_id (int): User identifier.
            notification (Notification): Notification object.
        """
        await self.pubsub_client._publish(
            f"user_{user_id}",
            notification.model_dump_json(exclude_none=True)
        )
        logger.info(f"Notification published through user_{user_id} redis channel")
    
    async def send_message(self, conversation_id: int, message: MessageData) -> None:
        """
        Sends a message to all users in a conversation.

        Args:
            conversation_id (str): Conversation identifier.
            message (str): Message to send.
        """
        await self.pubsub_client._publish(
            f"conversation_{conversation_id}",
            message.model_dump_json(exclude_none=True)
        )
        logger.info(f"Message published through conversation_{conversation_id} redis channel")
    
    async def remove_connection(self, ws_config: WebSocketConfig) -> None:
        """
        Removes a WebSocket connection from the WebSocketManager.

        Args:
            ws_config (WebSocketConfig): WebSocket configuration.
        """
        async with self.lock:
            try:
                logger.info(f"Removing WebSocket connection: {ws_config}")
                if ws_config.ws_type == WebSocketType.NOTIFICATIONS:
                    # Remove connection from notifications
                    if ws_config.user_id in self.notifications:
                        del self.notifications[ws_config.user_id]
                        await self.pubsub_client.unsubscribe(f"user_{ws_config.user_id}")
                        logger.info(f"Unsubscribed from user_{ws_config.user_id} redis channel")
                    # Remove connections from conversations
                    for conversation_id in self.conversations:
                        if ws_config.user_id in self.conversations[conversation_id]:
                            del self.conversations[conversation_id][ws_config.user_id]
                            if len(self.conversations[conversation_id].keys()) == 0:
                                await self.pubsub_client.unsubscribe(f"conversation_{conversation_id}")
                                logger.info(f"Unsubscribed from conversation_{conversation_id} redis channel")
                elif ws_config.ws_type == WebSocketType.CONVERSATION:
                    # Remove connection from conversations
                    if ws_config.conversation_id in self.conversations:
                        if ws_config.user_id in self.conversations[ws_config.conversation_id]:
                            del self.conversations[ws_config.conversation_id][ws_config.user_id]
                        if len(self.conversations[ws_config.conversation_id].keys()) == 0:
                            await self.pubsub_client.unsubscribe(f"conversation_{ws_config.conversation_id}")
                            logger.info(f"Unsubscribed from conversation_{ws_config.conversation_id} redis channel")
                logger.info(f"WebSocket connection removed: {ws_config}")
            except KeyError:
                logger.error("WebSocket connection not found")

    async def _pubsub_data_reader(self, pubsub_subscriber):
        """
        Reads and broadcasts messages received from Redis PubSub.

        Args:
            pubsub_subscriber (aioredis.ChannelSubscribe): PubSub object for the subscribed channel.
        """
        while True:
            try:
                async with self.lock:  # Ensure only one coroutine interacts with the subscriber
                    message = await pubsub_subscriber.get_message(ignore_subscribe_messages=True)
                if message is not None:
                    room_id: str = message['channel'].decode('utf-8')
                    if room_id.startswith("user_"):
                        user_id = int(room_id.removeprefix("user_"))
                        notification = Notification(**json.loads(message['data'].decode('utf-8')))
                        async with self.lock:
                            if user_id in self.notifications:
                                for connection in self.notifications[user_id]:
                                    await connection.send_json(notification.model_dump(exclude_none=True))
                    elif room_id.startswith("conversation_"):
                        conversation_id = int(room_id.removeprefix("conversation_"))
                        message_data = MessageData(**json.loads(message['data'].decode('utf-8')))
                        async with self.lock:
                            if conversation_id in self.conversations:
                                for user_id in self.conversations[conversation_id]:
                                    for connection in self.conversations[conversation_id][user_id]:
                                        await connection.send_json(ChatWebSocketResponse(
                                            type=ChatWebSocketResponseType.MESSAGE,
                                            message=message_data,
                                        ).model_dump(exclude_none=True))
            except Exception as e:
                logger.error(f"Error in _pubsub_data_reader: {e}")
                break


socket_manager = WebSocketManager()