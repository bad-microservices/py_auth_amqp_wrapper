import logging
import traceback

from tortoise import Tortoise

from jwt_helper import JWTEncoder, JWTValidator
from amqp_helper import AMQPConfig, AMQPService, new_amqp_func
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
    """This Function will run the auth_service

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

    logger = logging.getLogger("py_auth_amqp_wrapper")
    if log_config is not None:
        logger = getlogger(
            **log_config, disable_existing_loggers=disable_existing_loggers
        )
        logger.info("setup logger")

    sessionwf = SessionWorkflow(ldap_config, jwt_encoder, jwt_validator, app_config)
    session_workflow_get_access_token = new_amqp_func(
        queue_settings["session_workflow_get_access_token"], sessionwf.get_access_token
    )
    session_workflow_login = new_amqp_func(
        queue_settings["session_workflow_login"], sessionwf.login
    )
    session_workflow_logout = new_amqp_func(
        queue_settings["session_workflow_logout"], sessionwf.logout
    )

    userwf = UserWorkflow(jwt_validator, app_config)
    user_workflow_admin_create_user = new_amqp_func(
        queue_settings["user_workflow_admin_create_user"], userwf.admin_create_user
    )
    user_workflow_register_user = new_amqp_func(
        queue_settings["user_workflow_register_user"], userwf.register_user
    )
    user_workflow_delete_user = new_amqp_func(
        queue_settings["user_workflow_delete_user"], userwf.delete_user
    )
    user_workflow_change_user = new_amqp_func(
        queue_settings["user_workflow_change_user"], userwf.change_user
    )
    user_workflow_get_all = new_amqp_func(
        queue_settings["user_workflow_get_all"], userwf.get_all
    )
    user_workflow_get_user = new_amqp_func(
        queue_settings["user_workflow_get_user"], userwf.get_user
    )

    groupwf = GroupWorkflow(jwt_validator, app_config)
    group_workflow_add_user_to_group = new_amqp_func(
        queue_settings["group_workflow_add_user_to_group"], groupwf.add_user_to_group
    )
    group_workflow_remove_user_from_group = new_amqp_func(
        queue_settings["group_workflow_remove_user_from_group"],
        groupwf.remove_user_from_group,
    )
    group_workflow_create_group = new_amqp_func(
        queue_settings["group_workflow_create_group"], groupwf.create_group
    )
    group_workflow_delete_group = new_amqp_func(
        queue_settings["group_workflow_delete_group"], groupwf.delete_group
    )

    @session_workflow_logout.exception_handler(TypeError)
    @session_workflow_login.exception_handler(TypeError)
    @session_workflow_get_access_token.exception_handler(TypeError)
    async def handle_exception(*args, exc: Exception, **kwargs):
        logger.exception(exc, kwargs)
        return {"resp_code": 400, "resp_data": {"msg": "Invalid Data"}}

    @session_workflow_login.exception_handler(ValueError, PermissionError)
    async def handle_login_fail(*args, exc: Exception, **kwargs):
        logger.exception(exc, kwargs)
        return {"resp_code": 401, "resp_data": {"msg": "Could not login"}}

    @user_workflow_admin_create_user.exception_handler(Exception)
    @user_workflow_register_user.exception_handler(Exception)
    @user_workflow_delete_user.exception_handler(Exception)
    @user_workflow_change_user.exception_handler(Exception)
    @user_workflow_get_all.exception_handler(Exception)
    @user_workflow_get_user.exception_handler(Exception)
    @group_workflow_add_user_to_group.exception_handler(Exception)
    @group_workflow_remove_user_from_group.exception_handler(Exception)
    @group_workflow_create_group.exception_handler(Exception)
    @group_workflow_delete_group.exception_handler(Exception)
    @session_workflow_logout.exception_handler(Exception)
    @session_workflow_login.exception_handler(Exception)
    @session_workflow_get_access_token.exception_handler(Exception)
    async def handle_exception(*args, exc: Exception, **kwargs):
        logger.exception(exc, kwargs)
        return {"resp_code": 500, "resp_data": {"msg": f"something went wrong! {exc}"}}

    service = await AMQPService().connect(amqp_config)

    await service.register_function(session_workflow_get_access_token)
    await service.register_function(session_workflow_login)
    await service.register_function(session_workflow_logout)
    await service.register_function(user_workflow_admin_create_user)
    await service.register_function(user_workflow_register_user)
    await service.register_function(user_workflow_delete_user)
    await service.register_function(user_workflow_change_user)
    await service.register_function(user_workflow_get_all)
    await service.register_function(user_workflow_get_user)
    await service.register_function(group_workflow_add_user_to_group)
    await service.register_function(group_workflow_remove_user_from_group)
    await service.register_function(group_workflow_create_group)
    await service.register_function(group_workflow_delete_group)

    await service.serve()

    return
