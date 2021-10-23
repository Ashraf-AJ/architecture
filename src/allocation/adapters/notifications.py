from abc import ABC, abstractmethod
import smtplib

from allocation import config


class AbstractNotifications(ABC):
    @abstractmethod
    def send(self, destination, message):
        raise NotImplementedError


DEFAULT_HOST = config.get_email_host_and_port()["host"]
DEFAULT_PORT = config.get_email_host_and_port()["port"]


class EmailNotifications(AbstractNotifications):
    def __init__(self, smtp_host=DEFAULT_HOST, port=DEFAULT_PORT) -> None:
        self.server = smtplib.SMTP(smtp_host, port)
        self.server.noop()

    def send(self, destination, message):
        msg = f"Subject: allocation service notification\n {message}"
        self.server.sendmail(
            from_addr="allocation@example.com",
            to_addrs=[destination],
            msg=msg,
        )
