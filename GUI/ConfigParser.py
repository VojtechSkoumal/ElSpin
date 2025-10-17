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

def edit_config_file(section, key, value):
    ini_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', "ConfigFileLocal.ini")

    if not os.path.exists(ini_file_path):
        raise FileNotFoundError("Local config file does not exist. Cannot edit global config file.")
    else:
        logging.info(f"Using Local Config file: {ini_file_path}")
    config_parser = configparser.ConfigParser()
    config_parser.read(ini_file_path)

    if not config_parser.has_section(section):
        raise ValueError(f"Section '{section}' does not exist in the config file.")
    
    config_parser.set(section, key, value)

    with open(ini_file_path, 'w') as configfile:
        config_parser.write(configfile)
    logging.info(f"Updated [{section}] {key} = {value} in {ini_file_path}")
