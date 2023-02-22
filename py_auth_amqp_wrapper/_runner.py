import asyncio
import logging

from tortoise import Tortoise
from aio_pika import connect_robust
from aio_pika.patterns import JsonRPC

from jwt_helper import JWTEncoder, JWTValidator
from amqp_helper import AMQPConfig
from py_auth_micro.Config import DBConfig, AppConfig, LDAPConfig
from py_auth_micro.WorkFlows import SessionWorkflow, UserWorkflow, GroupWorkflow

from ._getlogger import getlogger


async def run(
    *,
    queue_settings: dict,
    jwt_encoder: JWTEncoder = None,
    jwt_validator: JWTValidator = None,
    db_config: DBConfig = DBConfig,
    app_config: AppConfig = AppConfig,
    ldap_config: LDAPConfig = None,
    amqp_config: AMQPConfig = AMQPConfig,
    log_config: logging.Logger = None,
    disable_existing_loggers=False,
):
    """This Function will run out auth_service

    Args:
        queue_settings (dict): Settings for the QUEUE-Names to use
        jwt_encoder (JWTEncoder, optional): JWT Encoder used for creating JWTs. Defaults to None.
        jwt_validator (JWTValidator, optional): JWTValidator used to verify JWTS. Defaults to None.
        db_config (DBConfig, optional): Database Configuration. Defaults to DBConfig.
        app_config (AppConfig, optional): General App Settings. Defaults to AppConfig.
        ldap_config (LDAPConfig, optional): Configuration for LDAP Interactions. Defaults to None.
        amqp_config (AMQPConfig, optional): Configuration for the AMQP Protocoll. Defaults to AMQPConfig.
        log_config (logging.Logger, optional): If given will configure the root logger. Defaults to None.
        disable_existing_loggers (bool, optional): Disables existing loggers. Defaults to False.
    """
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

    ######################
    #
    # Session Workflows
    #
    ######################
    await rpc.register(
        queue_settings["session_workflow_get_access_token"],
        sessionwf.get_access_token,
        auto_delete=True,
        durable=True,
        timeout=5,
    )
    await rpc.register(
        queue_settings["session_workflow_login"],
        sessionwf.login,
        auto_delete=True,
        durable=True,
        timeout=5,
    )
    await rpc.register(
        queue_settings["session_workflow_logout"],
        sessionwf.logout,
        auto_delete=True,
        durable=True,
        timeout=5,
    )

    ######################
    #
    # User Workflows
    #
    ######################

    await rpc.register(
        queue_settings["user_workflow_admin_create_user"],
        userwf.admin_create_user,
        auto_delete=True,
        durable=True,
        timeout=5,
    )
    await rpc.register(
        queue_settings["user_workflow_register_user"],
        userwf.register_user,
        auto_delete=True,
        durable=True,
        timeout=5,
    )
    await rpc.register(
        queue_settings["user_workflow_delete_user"],
        userwf.delete_user,
        auto_delete=True,
        durable=True,
        timeout=5,
    )
    await rpc.register(
        queue_settings["user_workflow_change_user"],
        userwf.change_user,
        auto_delete=True,
        durable=True,
        timeout=5,
    )
    await rpc.register(
        queue_settings["user_workflow_get_all"],
        userwf.get_all,
        auto_delete=True,
        durable=True,
        timeout=5,
    )
    await rpc.register(
        queue_settings["user_workflow_get_user"],
        userwf.get_user,
        auto_delete=True,
        durable=True,
        timeout=5,
    )

    ######################
    #
    # Group Workflows
    #
    ######################

    await rpc.register(
        queue_settings["group_workflow_add_user_to_group"],
        groupwf.add_user_to_group,
        auto_delete=True,
        durable=True,
        timeout=5,
    )
    await rpc.register(
        queue_settings["group_workflow_remove_user_from_group"],
        groupwf.remove_user_from_group,
        auto_delete=True,
        durable=True,
        timeout=5,
    )
    await rpc.register(
        queue_settings["group_workflow_create_group"],
        groupwf.create_group,
        auto_delete=True,
        durable=True,
        timeout=5,
    )
    await rpc.register(
        queue_settings["group_workflow_delete_group"],
        groupwf.delete_group,
        auto_delete=True,
        durable=True,
        timeout=5,
    )

    if log_config is not None:
        logger = getlogger(
            **log_config, disable_existing_loggers=disable_existing_loggers
        )
        logger.info("test")

    try:
        await asyncio.Future()
    finally:
        await connection.close()
    
