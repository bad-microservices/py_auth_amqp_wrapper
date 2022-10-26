import json
import base64

from jwt_helper import Issuer, load_key_from_disk, JWTEncoder, JWTValidator, SignMethod
from py_auth_micro.Config import DBConfig, AppConfig, LDAPConfig
from amqp_helper import AMQPConfig
from pathlib import Path

SECRET_METHODS = {
    "plain": lambda val: val,
    "base64plain": lambda val: base64.b64decode(val.encode("utf-8")).decode("utf8"),
    "base64key": base64.b64decode,
    "keyfile": load_key_from_disk,
}


def load_config(path_to_file: str) -> dict:
    raw_config: dict = json.loads(Path(path_to_file).read_text())

    jwt_validation = raw_config.get("jwt_validation", None)
    jwt_creation = raw_config.get("jwt_creation", None)
    ldap_settings = raw_config.get("ldap_settings", None)
    db_settings = raw_config.get("db_settings", None)
    amqp_settings = raw_config.get("amqp_settings", None)
    app_config = raw_config.get("app_config", None)

    config_dict = {}

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

    return config_dict
