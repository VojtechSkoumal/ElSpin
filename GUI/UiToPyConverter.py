import os
import logging

logger = logging.getLogger(__name__)

file_names = ["mainwindow"]

for file_name in file_names:
    file_name = os.path.join(os.path.dirname(__file__), file_name)

    try:
        if os.system(f'pyside6-uic -o "{file_name}".py "{file_name}".ui') != 0:
            raise Exception(f"Could not convert {file_name}.ui file to {file_name}.py file")
    except Exception:
        raise
    else:
        logger.debug(f"{__name__}: {file_name}.ui file converted to {file_name}.py file")
