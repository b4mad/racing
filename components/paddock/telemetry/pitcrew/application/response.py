class Response:
    MESSAGE = "message"
    PRIORITY = "priority"
    AT = "at"
    MAX_DISTANCE = "max_distance"

    def __init__(self, message, priority=0, max_distance=None, at=None):
        self.message = message
        self.at = at
        self.priority = priority
        self.max_distance = None

        self._sent = False
        self._discarded = False

    def send(self):
        self._sent = True

    def discard(self):
        self._discarded = True

    def response(self):
        response_dict = {self.MESSAGE: self.message, self.PRIORITY: self.priority}

        if self.at is not None:
            response_dict[self.AT] = self.at

        if self.max_distance is not None:
            response_dict[self.MAX_DISTANCE] = self.max_distance

        return response_dict


class ResponseInstant(Response):
    def __init__(self, message, **kwargs):
        super().__init__(message, **kwargs)
