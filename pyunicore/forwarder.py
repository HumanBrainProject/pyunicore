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
        self.parsed_url = _parse_forwarding_params(
            self.endpoint, service_port, service_host, login_node
        )
        self.transport = transport
        self.quiet = not debug
        self.local_port = 0
        self.service_socket = None
        self.client_socket = None

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

    def start_forwarding(self):
        self.quiet or print("Start forwarding.")
        threading.Thread(
            target=self.transfer, args=(self.client_socket, self.service_socket)
        ).start()
        threading.Thread(
            target=self.transfer, args=(self.service_socket, self.client_socket)
        ).start()

    def stop_forwarding(self):
        try:
            if self.client_socket:
                self.client_socket.close()
        except OSError:
            pass
        try:
            if self.service_socket:
                self.service_socket.close()
        except OSError:
            pass

    def transfer(self, source, destination):
        desc = f"{source.getpeername()} --> {destination.getpeername()}"
        self.quiet or print("Start TCP forwarding %s" % desc)
        buf_size = 32768
        while True:
            try:
                buffer = source.recv(buf_size)
                if len(buffer) > 0:
                    destination.send(buffer)
                elif len(buffer) == 0:
                    self.quiet or print("Source is at EOF for %s" % desc)
                    break
            except OSError as e:
                self.quiet or print("I/O ERROR for %s " % desc, e)
                for s in source, destination:
                    try:
                        s.close()
                    except OSError:
                        pass
                break
        self.quiet or print("Stopping TCP forwarding %s" % desc)

    def run(self, local_port):
        """open a listener, accept client connections and forward them to the backend"""
        with socket.socket() as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("", local_port))
            if local_port == 0:
                print("Listening on %s" % str(server.getsockname()))
            self.local_port = server.getsockname()[1]
            server.listen(2)
            while True:
                self.quiet or print("Waiting for client connection.")
                self.client_socket, _ = server.accept()
                self.quiet or print("Client %s connected." % str(self.client_socket.getpeername()))
                self.service_socket = self.connect()
                self.start_forwarding()


def _parse_forwarding_params(endpoint, service_port=None, service_host=None, login_node=None):
    """If not already present in the endpoint, the parameters like
    service_port are added.

    Returns:
        parsed URL with query parameters added as needed
    """
    parsed_url = urlparse(endpoint)
    q = parsed_url.query
    if service_port is not None and "port=" not in endpoint:
        if len(q) > 0:
            q += "&"
        q += "port=%d" % service_port
    if service_host is not None and "host=" not in endpoint:
        if len(q) > 0:
            q += "&"
        q += "host=%s" % service_host
    if login_node is not None and "loginNode=" not in endpoint:
        if len(q) > 0:
            q += "&"
        q += "loginNode=%s" % login_node
    return parsed_url._replace(query=q)


def open_tunnel(job, service_port=None, service_host=None, login_node=None, debug=False):
    """open a tunnel to a service running on the HPC side
    and return the connected socket
    """
    endpoint = job.links["forwarding"]
    tr = job.transport._clone()
    tr.use_security_sessions = False
    forwarder = Forwarder(tr, endpoint, service_port, service_host, login_node, debug)
    return forwarder.connect()


def run_forwarder(tr, local_port, endpoint, debug):
    """Starts a loop listening on 'local_port' for client connections.
    It connect clients to the backend 'endpoint'

    Args:
        transport: the transport (security sessions should be OFF)
        local_port: local port to listen on (use 0 to listen on any free port)
        endpoint: UNICORE REST API endpoint which can establish the forwarding
        debug: set to True for some debug output to the console
    """
    Forwarder(tr, endpoint, debug=debug).run(local_port)


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
    parser.add_argument(
        "-p",
        "--password",
        nargs="?",
        const="__ASK__",
        help="Authentication: password (leave empty to enter interactively)",
    )
    parser.add_argument("-i", "--identity", help="Authentication: private key file")
    args = parser.parse_args()

    port = int(args.listen)
    endpoint = args.endpoint
    password = args.password
    if "__ASK__" == password:
        import getpass

        password = getpass.getpass("Enter password:")
    credential = create_credential(args.username, password, args.token, args.identity)
    tr = Transport(credential, use_security_sessions=False)
    run_forwarder(tr, port, endpoint, args.debug)


if __name__ == "__main__":
    main()
