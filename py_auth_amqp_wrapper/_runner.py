import asyncio

from tortoise import Tortoise
from aio_pika import connect_robust
from aio_pika.patterns import JsonRPC

from jwt_helper import JWTEncoder, JWTValidator
from amqp_helper import AMQPConfig
from py_auth_micro.Config import DBConfig, AppConfig, LDAPConfig
from py_auth_micro.WorkFlows import SessionWorkflow, UserWorkflow, GroupWorkflow

async def run(
    *,
    jwt_encoder: JWTEncoder = None,
    jwt_validator: JWTValidator = None,
    db_config: DBConfig = DBConfig,
    app_config: AppConfig = AppConfig,
    ldap_config: LDAPConfig = None,
    amqp_config: AMQPConfig = AMQPConfig
):
    await Tortoise.init(
        config={
            "connections": db_config.to_dict("default"),
            "apps": {
                "models": {
                    "models": ["py_auth_micro.Models"],
                    "default_connection": "default",
                }
            },
        }
    )

    sessionwf = SessionWorkflow(ldap_config, jwt_encoder, jwt_validator, app_config)
    userwf = UserWorkflow(jwt_validator, app_config)
    groupwf = GroupWorkflow(jwt_validator, app_config)

    connection = await connect_robust(**amqp_config.aio_pika())

    channel = await connection.channel()
    rpc = await JsonRPC.create(channel)

    await rpc.register(
        "token",
        sessionwf.get_access_token,
        auto_delete=True,
        durable=True,
        timeout=5,
    )
    await rpc.register(
        "login", sessionwf.login, auto_delete=True, durable=True, timeout=5
    )
    await rpc.register(
        "logout", sessionwf.logout, auto_delete=True, durable=True, timeout=5
    )

    print("started")
    try:
        await asyncio.Future()
    finally:
        await connection.close()


    pass
