import json
import base64
import logging

from jwt_helper import Issuer, load_key_from_disk, JWTEncoder, JWTValidator, SignMethod
from py_auth_micro.Config import DBConfig, AppConfig, LDAPConfig
from amqp_helper import AMQPConfig
from pathlib import Path

from ._getlogger import getlogger

SECRET_METHODS = {
    "plain": lambda val: val,
    "base64plain": lambda val: base64.b64decode(val.encode("utf-8")).decode("utf8"),
    "base64key": base64.b64decode,
    "keyfile": load_key_from_disk,
}


def load_config(path_to_file: str) -> dict:
    """This Functions loads our Json Config and converts it into an dict.

    Some Configuration Parts will be converted into the corresponding config clases like LDAPConfig, APPConfig, DBConfig and AMQPConfig.

    Args:
        path_to_file (str): Filepath of the configuration File

    Raises:
        ValueError: If a Config Part is missing or invalid

    Returns:
        dict: Dictionary Containing all relevant Configuration Parts
    """
    raw_config: dict = json.loads(Path(path_to_file).read_text())

    jwt_validation = raw_config.get("jwt_validation", None)
    jwt_creation = raw_config.get("jwt_creation", None)
    ldap_settings = raw_config.get("ldap_settings", None)
    db_settings = raw_config.get("db_settings", None)
    amqp_settings = raw_config.get("amqp_settings", None)
    app_config = raw_config.get("app_config", None)
    queue_settings = raw_config.get("queue_settings", None)
    log_settings = raw_config.get("log_settings", None)

    config_dict = {}

    default_queue_names = {
        "session_workflow_login": "login",
        "session_workflow_logout": "logout",
        "session_workflow_get_access_token": "token",
        "user_workflow_register_user": "user_register",
        "user_workflow_admin_create_user": "user_admin_create",
        "user_workflow_delete_user": "user_delete",
        "user_workflow_change_user": "user_change",
        "user_workflow_get_all": "user_all",
        "user_workflow_get_user": "user_get",
        "group_workflow_add_user_to_group": "group_add_user",
        "group_workflow_remove_user_from_group": "group_remove_user",
        "group_workflow_create_group": "group_create",
        "group_workflow_delete_group": "group_delete",
    }

    if jwt_validation is not None:
        jwt_validator = JWTValidator()

        for issuer in jwt_validation:
            # translate sign methods
            methods = []
            for method in issuer["methods"]:
                methods.append(SignMethod[method])
            # load key the specified way
            key_type = issuer["secret"]["type"]
            secret_value = issuer["secret"]["value"]

            if not (
                key_type == "keyfile"
                or key_type == "base64plain"
                or key_type == "base64key"
                or key_type == "plain"
            ):
                raise ValueError(f"keytype {key_type} not supported")
            secret = SECRET_METHODS[key_type](secret_value)

            jwt_validator.add_issuer(Issuer(issuer["name"], secret, methods))

        config_dict["jwt_validator"] = jwt_validator

    if jwt_creation is not None:

        # get secret for signing
        key_type = jwt_creation["secret"]["type"]
        secret_value = jwt_creation["secret"]["value"]
        key_secret = jwt_creation["secret"].get("secret", None)

        if not (
            key_type == "keyfile"
            or key_type == "base64plain"
            or key_type == "base64key"
            or key_type == "plain"
        ):
            raise ValueError(f"keytype {key_type} not supported")

        if key_secret is not None:
            secret = SECRET_METHODS[key_type](secret_value, key_secret)
        else:
            secret = SECRET_METHODS[key_type](secret_value)

        # get sign method for signing
        sign_method = SignMethod[jwt_creation["signmethod"]]

        # create jwtencoder
        config_dict["jwt_encoder"] = JWTEncoder(
            jwt_creation["issuer"], sign_method, secret
        )

    if ldap_settings is not None:
        config_dict["ldap_config"] = LDAPConfig(**ldap_settings)

    if db_settings is not None:
        config_dict["db_config"] = DBConfig(**db_settings)

    if app_config is not None:
        config_dict["app_config"] = AppConfig(**app_config)

    if amqp_settings is not None:
        config_dict["amqp_config"] = AMQPConfig(**amqp_settings)

    if queue_settings is not None:
        for key, value in queue_settings.items():
            default_queue_names[key] = value

    if log_settings is not None:

        LEVELMAP = {
            "NOTSET": logging.NOTSET,
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }

        if log_settings.get("disable_aio_pika", False):
            pass

        if log_settings.get("disable_tortoise_orm", False):
            logging.getLogger("db_client").disabled = True
            logging.getLogger("tortoise").disabled = True

        level = LEVELMAP[log_settings.get("level", "INFO")]
        handler = log_settings.get("handler", None)
        handler_settings = log_settings.get("handler_settings", {})

        if handler_settings.get("amqp", None) is not None:
            amqp_settings = AMQPConfig(**handler_settings["amqp"])
            handler_settings = {"amqp_config": amqp_settings}

        config_dict["log_config"] = {
            "log_level": level, "handler": handler, "handler_config": handler_settings}

    config_dict["queue_settings"] = default_queue_names

    return config_dict
