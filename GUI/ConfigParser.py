import os
import configparser
import logging
logger = logging.getLogger(__name__)

def get_config_parser():
    ini_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', "ConfigFileLocal.ini")

    if not os.path.exists(ini_file_path):
        ini_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', "ConfigFile.ini"
        )
        logging.info(f'Using Global Config file: {ini_file_path}')
    else:
        logging.info(f"Using Local Config file: {ini_file_path}")
    config_parser = configparser.ConfigParser()
    config_parser.read(ini_file_path)

    return config_parser