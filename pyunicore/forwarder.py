""" Port forwarding utility methods """
import socket
import ssl
import threading
from urllib.parse import urlparse

from pyunicore.client import Transport
from pyunicore.credentials import UsernamePassword


class Forwarder:
    """Forwarding helper"""

    def __init__(self, transport, endpoint, service_port=None, service_host=None, debug=False):
        """Creates a new Forwarder instance"""
        self.endpoint = endpoint
        self.parsed_url = urlparse(self.endpoint)
        self.transport = transport
        self.quiet = not debug
        q = self.parsed_url.query
        if service_port is not None:
            if len(q) > 0:
                q += "&"
            q += "port=%d" % service_port
        if service_host is not None:
            if len(q) > 0:
                q += "&"
            q += "host=%s" % service_host
        self.parsed_url = self.parsed_url._replace(query=q)

    def connect(self):
        """connect to the backend service and return the connected socket"""
        sock = self.create_socket()
        msg = [
            f"GET {self.parsed_url.path}?{self.parsed_url.query} HTTP/1.1",
            "Host: %s" % self.parsed_url.netloc,
            "Connection: Upgrade",
            "Upgrade: UNICORE-Socket-Forwarding",
        ]
        headers = self.transport._headers({})
        for h in headers:
            msg.append(f"{h}: {headers[h]}")
        msg.append("")
        for m in msg:
            self.quiet or print("<-- %s" % m)
            sock.write(bytes(m + "\r\n", "UTF-8"))
        reader = sock.makefile("r")
        first = True
        code = -1
        while True:
            line = reader.readline().strip()
            self.quiet or print("--> %s" % line)
            if len(line) == 0:
                break
            if first:
                code = int(line.split(" ")[1])
                first = False
        if code != 101:
            raise ValueError(
                "Backend returned HTTP %s, could not handle UNICORE-Socket-Forwarding" % code
            )
        self.quiet or print("Connected to backend service.")
        return sock

    def create_socket(self):
        self.quiet or print("Connecting to %s" % self.parsed_url.netloc)
        address = tuple(self.parsed_url.netloc.split(":"))
        sock = socket.create_connection(address)
        if "https" == self.parsed_url.scheme:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            context.verify_mode = ssl.CERT_NONE
            context.check_hostname = False
            context.load_default_certs()
            sock = context.wrap_socket(sock)
        return sock

    def start_forwarding(self, socket1, socket2):
        self.quiet or print("Start forwarding.")
        threading.Thread(target=self.transfer, args=(socket1, socket2)).start()
        threading.Thread(target=self.transfer, args=(socket2, socket1)).start()

    def transfer(self, source, destination):
        desc = f"{source.getpeername()} --> {destination.getpeername()}"
        while True:
            try:
                buffer = source.recv(4096)
                if len(buffer) > 0:
                    destination.send(buffer)
                elif len(buffer) <= 0:
                    break
            except OSError:
                break
        self.quiet or print("Stopping TCP forwarding %s" % desc)


def main():
    """
    currently for TESTING ONLY - always authenticates as "demouser:test123"

    Main function to listen on a local port for a client connection.
    Once the client connects, the tool contacts the server and negotiates
    the port forwarding
    """
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("endpoint", help="UNICORE REST API endpoint")
    parser.add_argument("-L", "--listen", required=True, help="local port to listen on")
    parser.add_argument(
        "-d", "--debug", required=False, action="store_true", help="print debug info"
    )
    args = parser.parse_args()

    port = int(args.listen)
    endpoint = args.endpoint

    tr = Transport(UsernamePassword("demouser", "test123"), use_security_sessions=False)
    forwarder = Forwarder(tr, endpoint, debug=args.debug)
    quiet = not args.debug
    with socket.socket() as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("", port))
        server.listen(0)
        quiet or print("Waiting for client connection.")
        client_socket, _ = server.accept()
    quiet or print("Client connected.")
    service_socket = forwarder.connect()
    forwarder.start_forwarding(client_socket, service_socket)


if __name__ == "__main__":
    main()
