from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import yaml
import logging
from symbol import Symbol
import os


logger = logging.getLogger('tradebot.watchdog')

class FsHandler(FileSystemEventHandler):
    def __init__(self, config_file, sess):
        super().__init__()
        self.sess = sess
        self.config_file = config_file

    def on_modified(self, event):
        if self.config_file != event.src_path:
            return

        logger.info(f'{event.event_type}  file: {event.src_path}')
        try:
            with open(self.config_file, "r") as file:
                config = yaml.safe_load(file)
            ref = config.get('global_reference', None)
            symbols = {symbol_name: Symbol(symbol_name, symbol_config, ref=ref) for symbol_name, symbol_config in config['symbols'].items()}
            self.sess.symbols = symbols
            logger.info(f"Apply new symbols config from {self.config_file}:\n{yaml.dump(config['symbols'], indent=4)}")

        except Exception as e:
            logger.warning(f"Failed to read and apply new config {self.config_file}")
            logger.warning(e)
            logger.warning('Skip.')
        pass

def start_config_watchdog(config_file, sess):
    event_handler = FsHandler(config_file, sess)
    observer = Observer()
    dir_name = os.path.dirname(os.path.abspath(config_file))
    observer.schedule(event_handler, path=dir_name, recursive=False)
    observer.start()