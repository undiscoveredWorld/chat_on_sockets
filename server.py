"""
Server of chat.

List of classes:
    User
    Message

List of functions:
    check_free_positions
    get_user
    send_message
    send_message_history
    event_loop

List of constants:
    PORT
    COUNT_OF_CLIENTS

List of variables:
    users
    message_history
    server_socket
"""

import logging
from dataclasses import dataclass
from selectors import EVENT_READ, DefaultSelector
from socket import socket
from typing import Callable

HOST: str = ''
PORT: int = 9090
COUNT_OF_CLIENTS: int = 4
SERVER_SOCKET: socket = socket()

_names_list: list[str] = ["John", "Jill", "Smith", "Bella"]
users: list["User"] = []
message_history: list["Message"] = []

connection_selector = DefaultSelector()
get_message_selector = DefaultSelector()
send_message_selector = DefaultSelector()


@dataclass
class User:
    """
    User stores information about connected user.

    List of fields:
        client_socket
        name

    List of methods:
        del_self
    """

    client_socket: socket
    name: str

    def __init__(self, client_socket: socket):
        """
        Set all variables to arguments.

        :param client_socket: client socket of user
        """
        self.client_socket = client_socket
        self.name = _generate_name()


@dataclass
class Message:
    """
    Message stores information about message.

    List of fields:
        body
        sender
    """

    body: str
    sender: User


@dataclass
class _Handler:
    """
    _Handler stores information about handler.

    List of fields:
        function
        args
    """

    function: Callable
    args: list


def check_free_positions() -> bool:
    """
    Return true, if there are free positions, otherwise return false.

    :return: true, if there are free positions, otherwise return false
    """
    return len(_names_list) != 0


def _accept_connection():
    """
    Accept connection from client, send message history to it.

    Side effects:
        new user will append in users
        client_socket will be register in selector

    Error occur, when server is full. User will get message about it

    :return:
    """
    while True:
        yield

        client_socket: socket
        client_socket, _ = SERVER_SOCKET.accept()

        if not check_free_positions():
            send_message(client_socket, "Server is full. You will disconnect\n")
            logging.info("Got new connection, but server is full")
            client_socket.close()
            continue

        new_user = User(client_socket)
        users.append(new_user)
        logging.info("Accepted new connection. Places left: %d", len(_names_list))
        logging.info("%s:%d connected", *client_socket.getpeername())

        send_message(client_socket, f"Your name: {new_user.name}\n")
        send_message_history(client_socket)

        get_message = _get_message(client_socket)
        handler = _Handler(next, [get_message])
        get_message_selector.register(client_socket, EVENT_READ, data=handler)


def _generate_name() -> str:
    """
    Generate a random name.

    :return: generated name
    """
    return _names_list.pop()


def get_user(client_socket: socket) -> User:
    """
    Get user from socket.

    User is searched in users

    :param client_socket: socket object for search
    :raises: ValueError if user doesn't exist
    :return: searched user or None
    """
    for user in users:
        if user.client_socket == client_socket:
            return user
    else:
        raise ValueError("No user found")


def del_user(user: User) -> None:
    """
    Delete user.

    Deletes user from users, returns name in _names_list, and closed client
    socket
    """
    users.remove(user)
    _names_list.insert(0, user.name)
    user.client_socket.close()


def _get_message(client_socket: socket):
    while True:
        yield
        message_str = client_socket.recv(4096)

        if not message_str:
            get_message_selector.unregister(client_socket)

            user = get_user(client_socket)
            if user:
                del_user(user)

            client_socket.close()

            logging.info("Client disconnected. Places left: %d", len(_names_list))
        else:
            user = get_user(client_socket)
            if not user:
                return

        message = Message(message_str.decode(), user)
        message_history.append(message)

        for user_in_list in users:
            send_message(
                user_in_list.client_socket,
                f"{user.name}:{message_str.decode()}"
            )

        logging.info("Message got")


def send_message(client_socket: socket, message: str) -> None:
    """
    Send message to client.

    :param client_socket: client for getting message.
    :param message: message to send
    :return: None
    """
    client_socket.send(message.encode())


def send_message_history(client_socket: socket) -> None:
    """
    Send message history to client.

    :param client_socket: client for getting message history
    :return: None
    """
    for message in message_history:
        send_message(client_socket, f"{message.sender.name}:{message.body}")


def event_loop() -> None:
    """
    Run event loop.

    :return: None
    """
    while True:
        connection_keys = connection_selector.select(0.5)
        for key, _ in connection_keys:
            func = key.data.function
            func(*key.data.args)

        get_message_keys = get_message_selector.select(1)
        for key, _ in get_message_keys:
            func = key.data.function
            func(*key.data.args)


if __name__ == "__main__":
    SERVER_SOCKET.bind(("0.0.0.0", PORT))
    SERVER_SOCKET.listen(COUNT_OF_CLIENTS)

    logging.basicConfig(level=logging.INFO)

    logging.info("Server is listening on port %d", PORT)
    logging.info("Server can accept %s connections", COUNT_OF_CLIENTS)

    accept = _accept_connection()

    connection_selector.register(
        SERVER_SOCKET,
        EVENT_READ,
        data=_Handler(next, [accept])
    )

    event_loop()
