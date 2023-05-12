import logging


class LoggingMixin:
    def log(self, level, msg, *args, **kwargs):
        msg = f"{self.session_id}: {msg}"
        logging.log(level, msg, *args, **kwargs)

    def log_debug(self, message, *args, **kwargs):
        self.log(logging.DEBUG, message, *args, **kwargs)

    def log_error(self, message, *args, **kwargs):
        self.log(logging.DEBUG, message, *args, **kwargs)

    def log_info(self, message, *args, **kwargs):
        self.log(logging.DEBUG, message, *args, **kwargs)
