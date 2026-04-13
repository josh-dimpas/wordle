from typing import Any
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class WebSocketService:
    @staticmethod
    def _safe_broadcast(group_name: str, event_type: str, data: dict[str, Any]):
        try:
            channel_layer = get_channel_layer()
            if channel_layer is None:
                return
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "group_message",
                    "event_type": event_type,
                    "data": data,
                },
            )
        except Exception:
            pass

    @staticmethod
    def broadcast_to_lobby(lobby_code: str, event_type: str, data: dict[str, Any]):
        if not lobby_code:
            return
        WebSocketService._safe_broadcast(f"lobby:{lobby_code}", event_type, data)

    @staticmethod
    def broadcast_to_match(match_id: int, event_type: str, data: dict[str, Any]):
        if not match_id:
            return
        WebSocketService._safe_broadcast(f"match:{match_id}", event_type, data)

    @staticmethod
    def send_to_user(user_id: int, event_type: str, data: dict[str, Any]):
        if not user_id:
            return
        WebSocketService._safe_broadcast(f"user:{user_id}", event_type, data)

    @staticmethod
    def send_to_users(user_ids: list[int], event_type: str, data: dict[str, Any]):
        for user_id in user_ids:
            WebSocketService.send_to_user(user_id, event_type, data)

    @staticmethod
    def _safe_group_action(action: str, group_name: str, channel_name: str):
        try:
            channel_layer = get_channel_layer()
            if channel_layer is None:
                return
            action(channel_layer, group_name, channel_name)
        except Exception:
            pass

    @staticmethod
    def join_lobby_group(lobby_code: str, channel_name: str):
        if not lobby_code:
            return
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_add)(f"lobby:{lobby_code}", channel_name)

    @staticmethod
    def leave_lobby_group(lobby_code: str, channel_name: str):
        if not lobby_code:
            return
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_discard)(
                f"lobby:{lobby_code}", channel_name
            )

    @staticmethod
    def join_match_group(match_id: int, channel_name: str):
        if not match_id:
            return
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_add)(f"match:{match_id}", channel_name)

    @staticmethod
    def leave_match_group(match_id: int, channel_name: str):
        if not match_id:
            return
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_discard)(
                f"match:{match_id}", channel_name
            )

    @staticmethod
    def join_user_group(user_id: int, channel_name: str):
        if not user_id:
            return
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_add)(f"user:{user_id}", channel_name)

    @staticmethod
    def leave_user_group(user_id: int, channel_name: str):
        if not user_id:
            return
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_discard)(f"user:{user_id}", channel_name)
