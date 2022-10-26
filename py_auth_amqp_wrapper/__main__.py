import argparse
import asyncio
import sys
import py_auth_micro

from typing import Optional

from ._version import __version__
from ._load_config import load_config
from ._runner import run



def cli() -> Optional[str]:
    parser = argparse.ArgumentParser(
        prog="py_auth_amqp_wrapper",
        description="This will start an auth server based on py_auth_micro and connect it to an AMQP message Broker",
    )
    parser.add_argument("--config","-c",help="path to the configuration file", default="./config.json",type=str)
    parser.add_argument("--version","-v",help="displays the package version and quits",action="store_true")
    
    inputvars = parser.parse_args()

    if inputvars.version:
        print(f"py_auth_micro=={__version__}")
        return None

    return inputvars.config


if __name__ == "__main__":
    val = cli()

    if val is None:
        sys.exit(0)

        # configure DB
    print(f"""                             _   _     
                            | | | |    
  _ __  _   _     __ _ _   _| |_| |__  
 | '_ \| | | |   / _` | | | | __| '_ \ 
 | |_) | |_| |  | (_| | |_| | |_| | | |
 | .__/ \__, |   \__,_|\__,_|\__|_| |_|
 | |     __/ |_____                    
 |_|    |___/______|
       py_auth_micro: {py_auth_micro.__version__}
py_auth_amqp_wrapper: {__version__}
 
Starting Up!""")

    print(f"loading config file: '{val}'")
    try:
        config = load_config(val)
    except Exception:
        print("could not load config")
        sys.exit(78)
    print("loaded config")
    print("\n\nstarting up")
    asyncio.run(run(**config))
