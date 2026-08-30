"""Observer de RabbitMQ para EnergyShark."""

import json
import os
import ssl
import time
from pathlib import Path

import pika
import requests
from dotenv import load_dotenv


# Carga las variables guardadas en el archivo .env local.
load_dotenv()


# Si falta una variable en .env, se usa uno de estos valores de ejemplo.
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "broker.iic2173.org")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5671"))
RABBITMQ_VIRTUAL_HOST = os.getenv("RABBITMQ_VIRTUAL_HOST", "energy")

RABBITMQ_USER = os.getenv("RABBITMQ_USER", "usuario")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "contrasena")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "observer.X.q")
MASTER_URL = os.getenv("MASTER_URL", "http://localhost:8000/events")
HEALTH_FILE = Path("/tmp/connector-ready")


def send_to_master(body):
    """Envia el evento recibido a la API master."""
    event = json.loads(body.decode("utf-8"))
    return requests.post(MASTER_URL, json=event, timeout=10)


def on_message(channel, method, properties, body):
    """Muestra el mensaje, lo envia a master y confirma su recepcion."""
    print(body.decode("utf-8"), flush=True)

    try:
        response = send_to_master(body)

        if response.status_code in [200, 201, 409]:
            channel.basic_ack(delivery_tag=method.delivery_tag)
            print("Evento recibido correctamente por master.")
        elif response.status_code >= 500:
            print("Master no esta disponible:", response.status_code)
            time.sleep(5)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        else:
            print("Master rechazo el evento:", response.status_code)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except json.JSONDecodeError:
        print("El mensaje recibido no es un JSON valido.")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except requests.RequestException as error:
        print("No fue posible enviar el evento a master:", error)
        time.sleep(5)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def connect_to_rabbitmq():
    """Crea y devuelve una conexión segura con RabbitMQ."""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    ssl_context = ssl.create_default_context()

    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VIRTUAL_HOST,
        credentials=credentials,
        ssl_options=pika.SSLOptions(ssl_context, RABBITMQ_HOST),
    )

    return pika.BlockingConnection(parameters)


def start_observer():
    """Escucha la cola y vuelve a intentar si se pierde la conexión."""
    while True:
        try:
            print("Conectando con RabbitMQ...")
            connection = connect_to_rabbitmq()
            channel = connection.channel()
            channel.basic_qos(prefetch_count=1)

            channel.basic_consume(
                queue=RABBITMQ_QUEUE,
                on_message_callback=on_message,
                auto_ack=False,
            )

            HEALTH_FILE.touch()
            print("Observer esperando mensajes...")
            channel.start_consuming()
        except pika.exceptions.AMQPError as error:
            HEALTH_FILE.unlink(missing_ok=True)
            print("No fue posible mantener la conexión:", error)
            print("Nuevo intento en 5 segundos...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("Observer detenido.")
            break


if __name__ == "__main__":
    start_observer()
