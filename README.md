# Multiagente SAC (Integración Chatbot)

## Prerequisitos

- Python 3.12+
- Sqlite3 (Para ambiente DEV)
- ODBC MS SQL SERVER 17
- libmagic1
- libmagic-dev

### Instalación de driver ODBC MS SQL SERVER

0. Instalar paqueterias lsb_release y curl para uso de comandos

- Debian/Ubuntu
```bash
sudo apt-get update
sudo apt-get install lsb-release curl
```

- RHEL (Red Hat)
```bash
sudo dnf install epel-release -y
sudo dnf install lsb-release -y
sudo dnf install curl -y
```

1. Incluir las llaves de Microsoft para los packetes

- Debian/Ubuntu
```bash
 curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
```

2. Añadir repositorios al administrador de paquetes

- Debian
```bash
sudo add-apt-repository "deb [arch=amd64] https://packages.microsoft.com/debian/$(lsb_release -rs)/prod $(lsb_release -cs) main"
```

- Ubuntu
```bash
sudo add-apt-repository "deb [arch=amd64] https://packages.microsoft.com/ubuntu/$(lsb_release -rs)/prod $(lsb_release -cs) main"
```

- RHEL
```bash
curl https://packages.microsoft.com/config/rhel/$(lsb_release -rs)/prod.repo | sudo tee /etc/yum.repos.d/mssql-release.repo
```

3. Actualizar repositorios e instalar msodbcsql17

- Debian/Ubuntu
```bash
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql17
```

- RHEL
```bash
sudo yum remove unixODBC-utf16 unixODBC-utf16-devel #to avoid conflicts
sudo ACCEPT_EULA=Y yum install -y msodbcsql17
```

4. Verificar instalación

```bash
odbcinst -q -d -n "ODBC Driver 17 for SQL Server"
```

## Instalación libmagic
Libreria de sistema para la identificación de MIME types

```bash
sudo apt-get update
sudo apt-get install libmagic1 libmagic-dev
```

## Configuración de entorno Local
En la ruta _app/config.py_ encontraras las variables de configuración del aplicativo, por defecto se esta manejando la **sqlite_uri** sin embargo, en caso de necesitar configurar la conexión a una Base de Datos SQL SERVER asegurate de modificar **sqlserver_uri** según las credenciales que necesites para tu conexión y realiza el cambio de la variable que utiliza en la Clase DatabaseConnectionPool en la linea 15 del fichero _app/utilities/db.py_

```python
### Configuración SQLite
databases = {'multiagent': settings.sqlite_uri}
### Configuración SQL Server
databases = {'multiagent': settings.sqlserver_uri}
```

## Instalación de Librerias Python
Activa el ambiente virtual de tu eleccion, dentro del ambiente virtual

```bash
pip install -r requirements.txt
```

## Activación del proyecto
Con el siguiente comando se inicia el servidor para el back del multiagente
```bash
python -m app.main
```

Por defecto el proyecto inicia en el puerto 5001, puedes modificarlo en el fichero _app/main.py_ al final del archivo encontraras lo siguiente:

```python
uvicorn.run(
    "app.main:app",
    host="0.0.0.0",
    port=5001, # Aqui puedes cambiar el puerto por el que desees
    log_level="info",
    reload=True,
)
```


En caso de necesitar datos de prueba, puedes correr el siguiente comando, el cual carga los datos necesarios de estados y roles para el funcionamiento correcto del aplicativo, además de ello carga 100 usuarios (70 Agentes, 20 Supervisores, 10 Directores y 1 Administrador), asignaciones aleatorias de jerarquias, 30 conversaciones, 10 mensajes por conversación.

```bash
python -m app.utilities.fake_data 1 
```

Puedes omitir el 1 al final para no cargar los datos de estados y roles al sistema.

### Documentación Swagger

Para acceder a la documentación de la API puedes acceder a la siguiente ruta: `http://localhost:5001/docs 

## Despliegue en Docker
Para desplegar el proyecto en un contenedor de Docker, asegurate de tener instalado Docker, tener creado tu archivo .env y tener creado el archivo Dockerfile en la raiz del proyecto.

La estructura del archivo .env es la siguiente:
```bash
CHATBOT_URL=http://localhost:5000
FRONT_URL=http://localhost:3006
SENTRY_DSN=TU_URL_DE_SENTRY_PARA_REPORTES_DE_FALLOS
JWT_SECRET_KEY=TU_SECRET_VA_AQUI
JWT_REFRESH_SECRET_KEY=TU_REFRESH_VA_AQUI
JWT_RESET_SECRET_KEY=TU_RESET_VA_AQUI
JWT_EXPIRATION=120 # 2 Horas por defecto
JWT_REFRESH_EXPIRATION=1440 # 24 horas
JWT_RESET_EXPIRATION=1440 # 24 horas
MAX_ASSIGNMENTS_PER_AGENT=3 # Asignaciones maximas por agente, por defecto 3
# ROOT_PATH=
ENVIRONMENT=development # production o qa para iniciar logging en SENTRY 
SMTP_SENDER=test@example.com
SMTP_PASSWORD=********
# Cambiar la configuración del Host y puerto segun se necesite.
SMTP_HOST=smtp.gmail.com 
SMTP_PORT=587
```

Si necesitas desplegar unicamente el backend puedes crear la imagen del contenedor y correrla en el puerto deseado

```bash
# Crear la imagen del contenedor
docker build -t fastapi-backend .
# Correr la imagen del contenedor (puedes cambiar los puertos según sea necesario)
docker run -d -p 8000:8000 --name fastapi-backend fastapi-backend
```

En caso de que necesites hacer uso del aplicativo completo debes hacer uso del docker-compose.yaml donde encontraras la configuración de todos los contenedores necesarios para desplegar el aplicativo completo (Frontend, Backend, Redis, Nginx como proxy server).

```bash
# Crear la imagen del contenedor y correrlo
docker-compose up --build 
```

