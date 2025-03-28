from fastapi import Response
from app.config import settings
import json
import httpx

async def send_message(to_number: str, body: str, media_dict: dict = None, user_name: str = None) -> Response:
    """
    Sends a message to a WhatsApp number.

    Args:
    - to_number (str): The WhatsApp number to send the message to.
    - body (str): The message body.
    - media_dict (dict, optional): A dictionary containing the media URL. Defaults to None.

    Returns:
    - Response: The response from the API.
    """
    first_name = ' '.join(user_name.split(" ")[:2]) if user_name else ""
    data = {
        "to_number": to_number,
        "message": (f"*_{first_name}_*:\n" if first_name else "") + body
    }
    url = f"{settings.chatbot_url}/multiagent-to-whatsapp"
    headers = {
        "Content-Type": "application/json"
    }
    if not settings.testing:
        async with httpx.AsyncClient(verify=False) as client:
            if media_dict:
                data['media_url'] = media_dict['media_url']
            response = await client.post(url, json=data, headers=headers)
    else:
        response = Response(status_code=200, content=json.dumps({"status": True, "message":"Envio de mensaje correcto"}))
    return response


async def assing_agent_message(to_number: str, agent_name: str) -> Response:
    """
    Assigns an agent to a conversation and sends a message to the user.

    Args:
    - to_number (str): The WhatsApp number to send the message to.
    - agent_name (str): The name of the agent assigned to the conversation.

    Returns:
    - Response: The response from the API.
    """
    assigned_message = "Su conversación ha sido asignada a {agent_name}, quien le asistirá en un momento."

    data = {
        "to_number": to_number,
        "message": assigned_message.format(agent_name=agent_name)
    }
    url = f"{settings.chatbot_url}/multiagent-to-whatsapp"
    headers = {
        "Content-Type": "application/json"
    }
    if not settings.testing:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(url, json=data, headers=headers)
    else:
        response = Response(status_code=200, content=json.dumps({"status": True, "message":"Envio de mensaje correcto"}))
    return response


async def end_conversation(conversation_id: str, to_number: str, agent_name: str = "") -> Response:
    """
    Ends a conversation and sends a message to the user.

    Args:
    - conversation_id (str): The ID of the conversation to end.
    - to_number (str): The WhatsApp number to send the message to.
    - agent_name (str): The name of the agent who handled the conversation.

    Returns:
    - Response: The response from the API.
    """
    data = {
        "thread_id": conversation_id,
        "human": False,
        "to_number": to_number,
        "message": "Ha sido un gusto poder ayudarle con su consulta. Mi nombre es {}, y si necesita algo más, no dude en contactarnos. Que tenga un excelente día.".format(agent_name)
    }
    url = f"{settings.chatbot_url}/multiagent-to-end"
    headers = {
        "Content-Type": "application/json"
    }
    if not settings.testing:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(url, json=data, headers=headers)
    else:
        response = Response(status_code=200, content=json.dumps({"status": True, "message":"Envio de mensaje correcto"}))
    return response