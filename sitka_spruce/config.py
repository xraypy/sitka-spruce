#
# config for Sitka
from pathlib import Path
import yaml

from platformdirs import user_config_path

DEFAULT_CONFIG = {'dimreduce': {'maxdim': 5, 'method': 'single', 'point': 'mid'}}
def verify_configfile():
    "verify sitka configfile folder and file exist, making if needed"
    config_path =  user_config_path('sitka')
    if not config_path.exists():
        config_path.mkdir(mode=751, exist_ok=True)
    config_file  =  config_path / 'sitka.yaml'
    if not config_file.exists():
        with open(config_file, 'w') as fh:
            fh.write(yaml.safe_dump(DEFAULT_CONFIG))

def read_configfile():
    "read sitka configfile"
    verify_configfile()
    config_file = user_config_path('sitka') / 'sitka.yaml'
    return yaml.safe_load(open(config_file, 'r').read())
