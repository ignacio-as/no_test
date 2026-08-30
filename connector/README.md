# Observer de EnergyShark

Este componente escucha la cola personal de RabbitMQ, imprime cada mensaje y
lo envia a la API `master` para guardarlo en PostgreSQL.

## Archivos

- `observer.py`: contiene la conexión, la recepción y la reconexión.
- `requirements.txt`: contiene la librería necesaria para usar RabbitMQ.
- `.env`: guarda las credenciales locales y no se sube a Git.
- `.env.example`: muestra la estructura sin incluir credenciales reales.

## Cómo ejecutarlo

Desde la raíz del proyecto:

```powershell
pip install -r connector/requirements.txt
python connector/observer.py
```

Antes de ejecutarlo, abre el archivo `.env`, reemplaza `usuario`, `contrasena`
y cambia `observer.X.q` por la cola asignada. `MASTER_URL` debe apuntar a
`http://localhost:8000/events` cuando ambos componentes se ejecutan localmente.
El observer carga este archivo automaticamente mediante `python-dotenv`.

## Funcionamiento importante

1. Usa una conexión AMQP segura porque el broker trabaja en el puerto 5671.
2. Se conecta al virtual host indicado en `RABBITMQ_VIRTUAL_HOST`.
3. Escucha solamente la cola indicada en `RABBITMQ_QUEUE`.
4. Cuando llega un mensaje, lo imprime y lo convierte desde JSON.
5. Envia el evento a `POST /events` de la API `master`.
6. Confirma el mensaje a RabbitMQ solamente si `master` lo recibio.
7. Si la API no esta disponible, devuelve el evento a la cola para reintentarlo.
8. Si RabbitMQ deja de estar disponible, espera cinco segundos y vuelve a
   intentar la conexión.

## Trabajo pendiente

- Agregar el contenedor `connector` y su `HEALTHCHECK`.
- Cambiar `MASTER_URL` a `http://master:8000/events` dentro de Docker Compose.
