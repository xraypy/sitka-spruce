#
# config for Sitka

import yaml
from pathlib import Path
from platformdirs import user_config_path
from contextlib import suppress

DEFAULT_CONFIG = {'dimreduce': {'maxdim': 5,
                                'method': 'single',
                                'point': 'mid'}}
def verify_configfile():
    "verify sitka configfile folder and file exist, making if needed"
    config_path =  user_config_path('sitka_spruce',
                                    appauthor=False, ensure_exists=True)
    if not config_path.exists():
        config_path.mkdir(mode=493,  parents=True, exist_ok=True)
    config_file  =  Path(config_path, 'sitka.yaml')
    if not config_file.exists():
        with open(config_file, 'w') as fh:
            fh.write(yaml.safe_dump(DEFAULT_CONFIG))

def read_configfile():
    "read sitka configfile"
    conf = {k: v for k, v in DEFAULT_CONFIG.items()}  
    verify_configfile()
    config_file = Path(user_config_path('sitka_spruce'), 'sitka.yaml')
    with suppress(Exception):
        conf.update(yaml.safe_load(open(config_file, 'r').read()))

    return conf
    
    
