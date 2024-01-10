import socket
import logging
from selectors import DefaultSelector, EVENT_READ
from typing import Callable


class User:
    client_socket: socket.socket
    name: str

    def __init__(self, client_socket: socket.socket):
        self.client_socket = client_socket
        self.name = generate_name()

    def del_self(self):
        names_list.insert(0, self.name)
        self.client_socket.close()


class Message:
    body: str
    sender: User

    def __init__(self, body: str, sender: User):
        self.body = body
        self.sender = sender


class Handler:
    function: Callable
    args: list

    def __init__(self, function: Callable, args: list | None):
        self.function = function
        self.args = args or list()


PORT: int = 9090
COUNT_OF_CLIENTS: int = 4

names_list: list[str] = ["John", "Jill", "Smith", "Bella"]
users: list[User] = list()
message_history: list[Message] = list()

selector = DefaultSelector()
server_socket: socket.socket = socket.socket()
server_socket.bind(("", PORT))
server_socket.listen(COUNT_OF_CLIENTS)

logging.basicConfig(level=logging.INFO)

logging.info("Server is listening on port {}".format(PORT))
logging.info("Server can accept {} connections".format(COUNT_OF_CLIENTS))


def check_free_positions() -> bool:
    return len(names_list) != 0


def accept_connection() -> None:
    client_socket, _ = server_socket.accept()

    if not check_free_positions():
        send_message(client_socket, "Server is full. You will disconnect\n")
        logging.info("Got new connection, but server is full")
        client_socket.close()
        return

    users.append(User(client_socket))
    logging.info("Accepted new connection. Places left: {}".format(len(names_list)))
    logging.debug("{} connected".format(client_socket))

    send_message(client_socket, "Your name: {}\n".format(users[-1].name))
    send_message_history(client_socket)
    handler = Handler(get_message, [client_socket])
    selector.register(client_socket, EVENT_READ, data=handler)


def generate_name() -> str:
    return names_list.pop()


def get_user(client_socket: socket.socket) -> User:
    for user in users:
        if user.client_socket == client_socket:
            return user


def get_message(client_socket: socket.socket) -> None:
    message_str = client_socket.recv(4096)

    if not message_str:
        selector.unregister(client_socket)
        user = get_user(client_socket)
        users.remove(user)
        user.del_self()
        client_socket.close()
        logging.info("Client disconnected. Places left: {}".format(len(names_list)))
    else:
        user = get_user(client_socket)
        message = Message(message_str.decode(), user)
        message_history.append(message)
        for u in users:
            send_message(u.client_socket, "{}:{}".format(user.name, str(message_str.decode())))

        logging.info("Message got")


def send_message(client_socket: socket.socket, message: str):
    client_socket.send(message.encode())


def send_message_history(client_socket: socket.socket):
    for message in message_history:
        send_message(client_socket, "{}:{}".format(message.sender.name, message.body))


def event_loop():
    while True:
        keys = selector.select()

        for key, _ in keys:
            func = key.data.function
            func(*key.data.args)


selector.register(server_socket, EVENT_READ, data=Handler(accept_connection, None))
event_loop()
