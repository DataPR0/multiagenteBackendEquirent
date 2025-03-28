import msgpack
import json
import os
import sqlite3
from contextlib import closing
from msgpack import ExtType


def unpack_msgpack(data):
    try:
        unpacked_data = msgpack.unpackb(data)
        # print("Datos desempaquetados:", unpacked_data)
        return unpacked_data
    except Exception as e:
        print("Error al desempaquetar los datos:", e)


def ext_type_decoder(code, data):
    if code == 5:
        # Desempaquetar el binario contenido dentro de ExtType
        unpacked = msgpack.unpackb(data, raw=False)
        return {
            "code": code,
            "decoded_data": unpacked
        }
    # Si no es el código esperado, devolver como está
    return ExtType(code, data)


data = None
DB_PATH = 'checkpoints.db'
if (os.path.exists(DB_PATH)):
    with closing(sqlite3.connect(DB_PATH, check_same_thread=False)) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute("SELECT * FROM checkpoints ORDER BY thread_id DESC LIMIT 1;")
            data = cursor.fetchall()

    # print(data[0][5])
    messages = []
    unpacked = unpack_msgpack(data[0][5])
    for msg in (unpacked)['channel_values']['messages']:
        unpacked_msg = msgpack.unpackb(msg.data)
        messages.append(unpacked_msg)
    
    json_data = json.dumps(messages, indent=4)
    print("Datos en formato JSON:", json_data)