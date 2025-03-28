import uvicorn
import sentry_sdk
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers.conversations import conversations
from app.routers.users import users
from app.routers.auth import auth
from app.routers.chats import chats
from app.routers.notifications import notifications
from app.routers.info import info
from app.routers.webhook import webhook
from app.routers.templates import templates
from app.routers.admin import admin
from app.utilities.db import initialize_database



@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        initialize_database()
        yield
    finally:
        pass


if settings.environment != "development":
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for tracing.
        traces_sample_rate=1.0,
        _experiments={
            # Set continuous_profiling_auto_start to True
            # to automatically start the profiler on when
            # possible.
            "continuous_profiling_auto_start": True,
        },
        environment=settings.environment
    )


app = FastAPI(
    title="Multiagent API",
    description="RESTful API for multiagent project",
    version="0.1.0",
    root_path=settings.root_path,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.front_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    auth.router,
    tags=["auth"],
    prefix="/v1/auth"
)


app.include_router(
    conversations.router,
    tags=["conversations"],
    prefix="/v1/conversations",
    dependencies=[Depends(auth.get_current_user)]
)


app.include_router(
    info.router,
    tags=["info"],
    prefix="/v1/info",
    dependencies=[Depends(auth.get_current_user)]
)


app.include_router(
    users.router,
    tags=["users"],
    prefix="/v1/users",
    dependencies=[Depends(auth.get_current_user)]
)


app.include_router(
    chats.router,
    tags=["chats"],
    prefix="/v1/chats"
)


app.include_router(
    notifications.router,
    tags=["notifications"],
    prefix="/v1/notifications"
)

app.include_router(
    webhook.router,
    tags=["chatbot"],
    prefix="/v1/chatbot"
)

app.include_router(
    templates.router,
    tags=["templates"],
    prefix="/v1/templates",
    dependencies=[Depends(auth.get_current_user)]
)

app.include_router(
    admin.router,
    tags=["admin"],
    prefix="/v1/admin",
    dependencies=[
        Depends(auth.get_current_user),
        Depends(admin.check_if_user_is_admin)
    ]
)


if __name__ == '__main__':
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5001,
        log_level="info",
        reload=True,
    )