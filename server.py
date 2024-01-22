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
    HOST
    PORT

List of variables:
    users
    message_history
    count_of_clients
    server_socket
"""

import logging
from dataclasses import dataclass
from selectors import EVENT_READ, DefaultSelector
from socket import socket
from typing import Callable

HOST: str = ''
PORT: int = 9090

_names: list[str] = ["John", "Jill", "Smith", "Bella"]
users: list["User"] = []
sent_messages: list["Message"] = []
count_of_clients: int = len(_names)

server_socket: socket = socket()

_connection_selector = DefaultSelector()
_get_message_selector = DefaultSelector()


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


def _accept_connection():
    """
    Procedure to accept connection.

    Procedure accepts connection, creates and connects user, send user some messages
    and then creates handler for reading messages

    Side effects:
        new user will append in users
        client_socket will be register in selector

    Error occur, when server is full. User will get message about it

    :return:
    """
    while True:
        yield
        client_socket: socket
        client_socket, _ = server_socket.accept()

        # Handle no free positions case
        if not check_free_positions():
            send_message(
                client_socket,
                "Server is full. You will disconnect\n"
            )
            logging.info("Got new connection, but server is full")
            client_socket.close()
            continue

        new_user = _create_user(client_socket)
        users.append(new_user)

        send_message(client_socket, f"Your name: {new_user.name}\n")
        send_message_history(client_socket)

        # Subscribe on read socket event
        get_message = _get_message(client_socket)
        handler = _Handler(next, [get_message])
        _get_message_selector.register(client_socket, EVENT_READ, data=handler)

        logging.info(
            "Accepted new connection. Places left: %d",
            len(_names)
        )
        logging.info("%s:%d connected", *client_socket.getpeername())


def check_free_positions() -> bool:
    """
    Return true, if there are free positions, otherwise return false.

    :return: true, if there are free positions, otherwise return false
    """
    return len(_names) != 0


def _create_user(client_socket: socket) -> User:
    """
    Create user from client_socket.

    Side effects:
        Pop name from _names

    :param client_socket:
    :return:
    """
    name = _names.pop()
    user = User(
        client_socket=client_socket,
        name=name
    )
    return user


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
    for message in sent_messages:
        send_message(client_socket, f"{message.sender.name}:{message.body}")


def _get_message(client_socket: socket):
    """
    Procedure to receive messages from client socket.

    if message isn't sent, user disconnect
    This procedure receives message from client socket

    :param client_socket:
    :return:
    """
    while True:
        yield
        message_str = client_socket.recv(4096)

        if not message_str:
            _disconnect_socket(client_socket)
            return

        try:
            user = get_user(client_socket)
        except ValueError:
            _disconnect_socket(client_socket)
            return

        message = Message(message_str.decode(), user)
        sent_messages.append(message)

        for user_in_list in users:
            send_message(
                user_in_list.client_socket,
                f"{user.name}:{message_str.decode()}"
            )

        logging.info("Message got")


def _unsubscribe_socket(client_socket: socket):
    _get_message_selector.unregister(client_socket)
    client_socket.close()


def _disconnect_socket(client_socket: socket) -> None:
    try:
        user = get_user(client_socket)
        return_name(user.name)
        del_user(user)
    except ValueError:
        pass

    _unsubscribe_socket(client_socket)

    logging.info(
        "Client disconnected. Places left: %d",
        len(_names)
    )


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

    raise ValueError("No user found")


def del_user(user: User) -> None:
    """
    Delete user.

    Deletes user from users, returns name in _names_list, and closed client
    socket
    """
    try:
        users.remove(user)
    except ValueError:
        pass


def return_name(name: str):
    if name not in _names:
        _names.insert(0, name)


def event_loop() -> None:
    """
    Run event loop.

    :return: None
    """
    while True:
        connection_keys = _connection_selector.select(0.5)
        for key, _ in connection_keys:
            func = key.data.function
            func(*key.data.args)

        get_message_keys = _get_message_selector.select(1)
        for key, _ in get_message_keys:
            func = key.data.function
            func(*key.data.args)


if __name__ == "__main__":
    server_socket.bind(("0.0.0.0", PORT))
    server_socket.listen(count_of_clients)

    logging.basicConfig(level=logging.INFO)

    logging.info("Server is listening on port %d", PORT)
    logging.info("Server can accept %s connections", count_of_clients)

    accept = _accept_connection()

    _connection_selector.register(
        server_socket,
        EVENT_READ,
        data=_Handler(next, [accept])
    )

    event_loop()
