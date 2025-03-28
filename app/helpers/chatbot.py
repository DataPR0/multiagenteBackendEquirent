
import json
from contextlib import closing
from sqlalchemy import text

from app.helpers import messages
from app.models.message import Message, SenderTypeEnum
from app.utilities.db import get_session


def load_chatbot_messages(thread_id:str, conversation_id:int, last_message:str):
    with closing(next(get_session("multiagent"))) as session:
        result = session.execute(text(f"SELECT ch.\"checkpoint\" FROM sac.checkpoints ch WHERE thread_id='{thread_id}'"))
        resutl = result.all()
        for row in resutl:
            load_data(row, conversation_id, last_message)
        session.close()
    return None

def load_data(row, conversation_id, last_message):
    try:
        temp = row[0].replace("'", '"').replace("None", "null").replace("False", "false").replace("True", "true")
        temp = json.loads(temp)
        message_list = temp.get('channel_values').get('messages')
        print("Chatbot MSGS::::", messages)
        if message_list:
            for msg in message_list:
                if last_message != msg[2].get("content"):
                    messages.save_message(Message(
                        conversation_id=conversation_id,
                        content=msg[2].get("content"),
                        sender_type=SenderTypeEnum.CLIENT if msg[1] == "HumanMessage" else SenderTypeEnum.CHATBOT,
                        user=None
                    ), conversation_id)
                print("Human: " if msg[1] == "HumanMessage" else "Chatbot: " ,
                    msg[2].get("content"))
    except Exception as e:
        print("Error while loading Chatbot Messages", e)