
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
            filename: str = "LogOutput.log",
            mode: _Mode = ALL,
            level: _Level = INFO,
            file_level: _Level = DEBUG,
            stream_level: _Level = INFO,
            formatter: logging.Formatter | None = None,
            file_formatter: logging.Formatter | None = None,
            stream_formatter: logging.Formatter | None = None
        ):
        """
        ### name
        > logging.getLogger(name)

        ### mode
        > `ALL("all")`, `FILE("file")`, `CONSOLE("console")`

        ### level
        > logging.setLevel(level)

        ### file_formatter
        > *default* ***"[%(asctime)s][%(levelname)s]: %(message)s"***

        > *example* `[2025-01-01 12:34:56,641][INFO]: logoutput`

        ### stream_formatter
        > *default* ***"%(levelname)s: %(message)s"***

        > *example* `INFO: logoutput`
        """
        self.name = name
        self.filename = filename
        self.mode = mode
        self.level = level
        self.file_level = file_level
        self.stream_level = stream_level
        self.formatter = formatter
        self.file_formatter = file_formatter
        self.stream_formatter = stream_formatter
        # 日志器的主level 必须为最详细
        self.logger = logging.Logger(self.name)
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
            filename=self.filename,
            mode="a",
            encoding="utf-8",
            delay=True, # 第一次写入时打开
        )

        self.file_handler.setLevel(self.file_level)

        if self.file_formatter:
            file_formatter = self.file_formatter
        elif self.formatter:
            file_formatter = self.formatter
        else:
            file_formatter = logging.Formatter(
                "[%(asctime)s][%(levelname)s]:%(message)s"
            )

        self.file_handler.setFormatter(file_formatter)

        self.logger.addHandler(self.file_handler)

        return self.logger
    
    def _create_stream_logger(self):

        self.stream_handler = logging.StreamHandler()

        self.stream_handler.setLevel(self.stream_level)

        if self.stream_formatter:
            stream_formatter = self.stream_formatter
        elif self.formatter:
            stream_formatter = self.formatter
        else:
            stream_formatter = logging.Formatter(
                "%(levelname)s:%(message)s"
            )

        self.stream_handler.setFormatter(stream_formatter)

        self.logger.addHandler(self.stream_handler)

        return self.logger
    
    @staticmethod
    def to_str(*items):
        text = ""
        for item in items:
            t = str(item)
            text += " " + t
        return text

    def debug(self, *msgs):
        self.logger.debug(self.to_str(*msgs))

    def info(self, *msgs):
        self.logger.info(self.to_str(*msgs))

    def warning(self, *msgs):
        self.logger.warning(self.to_str(*msgs))

    def error(self, *msgs):
        self.logger.error(self.to_str(*msgs))

    def critical(self, *msgs):
        self.logger.critical(self.to_str(*msgs))

