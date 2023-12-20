import pathway as pw
import logging

class MqttClient():

    def __init__(self, subject) -> None:
        self._subject = subject

    def notify(self, topic, payload) -> None:
        self._subject.next_json(payload)

    def run(self) -> None:
        # start the mqtt client and subscribe to the topic
        logging.info("Starting client")
        self._subject.run()

class TelemetrySubject(pw.io.python.ConnectorSubject):
    def __init__(self) -> None:
        super().__init__()

    def set_client(self, client) -> None:
        self._mqtt_client = client

    def notify(self, topic, payload) -> None:
        self.next_json(payload)

    def run(self) -> None:
        logging.info("TelemetrySubject running")
        self._mqtt_client.run()

    def on_stop(self) -> None:
        pass
        # self._mqtt_client.disconnect()


class InputSchema(pw.Schema):
    key: int = pw.column_definition(primary_key=True)
    text: str

