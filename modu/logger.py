
import logging
from typing import Literal

# 日志记录器
class Logger:

    _Mode = Literal['all', 'file', 'console']
    ALL = "all"
    FILE = "file"
    CONSOLE = "console"

    _Level = Literal[10,20,30,40,50]
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    CRITICAL = 50

    def __init__(self, 
            name: str | None = "modu",
            mode: _Mode = ALL,
            level: _Level = INFO,
            file_level: _Level | None = None,
            stream_level: _Level | None = None,
            formatter: logging.Formatter | None = None,
            file_formatter: logging.Formatter | None = None,
            stream_formatter: logging.Formatter | None = None
        ):
        """
        name => logging.getLogger(name)

        mode => ALL("all"), FILE("file"), CONSOLE("console")

        level => logging.setLevel(level)
        """
        self.name = name
        self.mode = mode
        self.level = level
        self.file_level = file_level
        self.stream_level = stream_level
        self.formatter = formatter
        self.file_formatter = file_formatter
        self.stream_formatter = stream_formatter
        # 日志器的主level 必须为最详细
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.DEBUG)

        if self.mode == 'all':
            self._create_file_logger()
            self._create_stream_logger()
        elif self.mode == 'file':
            self._create_file_logger()
        elif self.mode == 'console':
            self._create_stream_logger()

    def _create_file_logger(self):

        self.file_handler = logging.FileHandler(
            filename="LogOutput.log",
            mode="a",
            encoding="utf-8",
            delay=True, # 第一次写入时打开
        )

        self.file_handler.setLevel(self.file_level or self.level)

        if self.file_formatter:
            file_formatter = self.file_formatter
        elif self.formatter:
            file_formatter = self.formatter
        else:
            file_formatter = logging.Formatter(
                "[%(asctime)s][%(levelname)s]: %(message)s"
            )

        self.file_handler.setFormatter(file_formatter)

        self.logger.addHandler(self.file_handler)

        return self.logger
    
    def _create_stream_logger(self):

        self.stream_handler = logging.StreamHandler()

        self.stream_handler.setLevel(self.stream_level or self.level)

        if self.stream_formatter:
            stream_formatter = self.stream_formatter
        elif self.formatter:
            stream_formatter = self.formatter
        else:
            stream_formatter = logging.Formatter(
                "%(levelname)s: %(message)s"
            )

        self.stream_handler.setFormatter(stream_formatter)

        self.logger.addHandler(self.stream_handler)

        return self.logger

    def debug(self, msg: str):
        self.logger.debug(msg)

    def info(self, msg: str):
        self.logger.info(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def critical(self, msg: str):
        self.logger.critical(msg)

log = Logger(level=Logger.DEBUG, file_level=Logger.DEBUG, stream_level=Logger.DEBUG)