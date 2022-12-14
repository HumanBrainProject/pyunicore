""" Port forwarding utility methods """
import socket
import ssl
import threading
from urllib.parse import urlparse

from pyunicore.client import Transport
from pyunicore.credentials import create_credential


class Forwarder:
    """Forwarding helper"""

    def __init__(
        self,
        transport,
        endpoint,
        service_port=None,
        service_host=None,
        login_node=None,
        debug=False,
    ):
        """Creates a new Forwarder instance
        The remote service host/port can be already encoded in the endpoint, or given separately

        Args:
            transport: the transport (security sessions should be OFF)
            endpoint: UNICORE REST API endpoint which can establish the forwarding
            service_port: the remote service port (if not already encoded in the endpoint)
            service_host: the (optional) remote service host (if not encoded in the endpoint)
            login_node: the /optional) login node to use (if not encoded in the endpoint)
            debug: set to True for some debug output to the console
        """
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
        if login_node is not None:
            if len(q) > 0:
                q += "&"
            q += "loginNode=%s" % service_host
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
            sock.write(bytes(m + "\r\n", "UTF-8"))
            if self.quiet:
                continue
            if m.startswith("Authorization"):
                print("<-- Authorization: ***")
            else:
                print("<--", m)
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
        if ":" in self.parsed_url.netloc:
            _addr = self.parsed_url.netloc.split(":")
            address = (_addr[0], int(_addr[1]))
        else:
            if "https" == self.parsed_url.scheme.lower():
                address = (self.parsed_url.netloc, 443)
            else:
                address = (self.parsed_url.netloc, 80)
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
        self.quiet or print("Start TCP forwarding %s" % desc)
        while True:
            try:
                buffer = source.recv(16384)
                if len(buffer) > 0:
                    destination.send(buffer)
                elif len(buffer) <= 0:
                    break
            except OSError:
                for s in source, destination:
                    try:
                        s.close()
                    except OSError:
                        pass
                break
        self.quiet or print("Stopping TCP forwarding %s" % desc)


def run_forwarder(tr, local_port, endpoint, debug):
    """Starts a loop listening on 'local_port' for client connections.
    It connect clients to the backend 'endpoint'

    Args:
        transport: the transport (security sessions should be OFF)
        local_port: local port to listen on (use 0 to listen on any free port)
        endpoint: UNICORE REST API endpoint which can establish the forwarding
        debug: set to True for some debug output to the console
    """
    forwarder = Forwarder(tr, endpoint, debug=debug)
    quiet = not debug
    with socket.socket() as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("", local_port))
        if local_port == 0:
            print("Listening on %s" % str(server.getsockname()))
        server.listen(2)
        while True:
            quiet or print("Waiting for client connection.")
            client_socket, _ = server.accept()
            quiet or print("Client %s connected." % str(client_socket.getpeername()))
            service_socket = forwarder.connect()
            forwarder.start_forwarding(client_socket, service_socket)


def main():
    """
    Main function to listen on a local port for a client connection.
    Once the client connects, the tool contacts the server and negotiates
    the port forwarding
    """
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("endpoint", help="Full UNICORE REST API endpoint for forwarding")
    parser.add_argument("-L", "--listen", required=True, help="local port to listen on")
    parser.add_argument(
        "-d", "--debug", required=False, action="store_true", help="print debug info"
    )
    parser.add_argument("-t", "--token", help="Authentication: token")
    parser.add_argument("-u", "--username", help="Authentication: username")
    parser.add_argument("-p", "--password", help="Authentication: password")
    parser.add_argument("-i", "--identity", help="Authentication: private key file")
    args = parser.parse_args()

    port = int(args.listen)
    endpoint = args.endpoint
    credential = create_credential(args.username, args.password, args.token, args.identity)
    tr = Transport(credential, use_security_sessions=False)
    run_forwarder(tr, port, endpoint, args.debug)


if __name__ == "__main__":
    main()
