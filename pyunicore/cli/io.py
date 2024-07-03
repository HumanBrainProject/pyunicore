""" Storage-related commands """

import re

from pyunicore.cli.base import Base
from pyunicore.client import PathFile
from pyunicore.client import Storage


class LS(Base):
    def add_command_args(self):
        self.parser.prog = "unicore ls"
        self.parser.description = self.get_synopsis()
        self.parser.add_argument("remote_dirs", help="Remote directories to list", nargs="*")
        self.parser.add_argument(
            "-l",
            "--long",
            required=False,
            action="store_true",
            help="detailed listing",
        )

    def get_synopsis(self):
        return """List directories on UNICORE storage(s)."""

    def get_description(self):
        return "list directories"

    def get_group(self):
        return "Data management"

    def split_storage_url(self, url: str):
        base = re.match(r"(https://\S+/rest/core/storages/).*", url).group(1)
        storage_id = re.match(r"https://\S+/rest/core/storages/(\S+).*", url).group(1)
        tok = storage_id.split("/files")
        storage_id = tok[0]
        path = tok[1] if len(tok) > 1 else "/"
        return base + storage_id, path

    def _detailed(self, name, p):
        d = "d" if p["isDirectory"] is True else "-"
        print(f"{d}{p['permissions']} {p['size']} {p['lastAccessed']} {name}")

    def print_single(self, p: PathFile):
        if self.args.long is True:
            self._detailed(p.name, p.properties)
        else:
            print(p.name)

    def run(self, args):
        super().setup(args)
        for endpoint in self.args.remote_dirs:
            storage_url, file_path = self.split_storage_url(endpoint)
            self.verbose(f"Listing: {file_path} on {storage_url}")
            storage = Storage(self.credential, storage_url=storage_url)
            p = storage.stat(file_path)
            if p.isdir():
                ls = storage.contents(path=p.name)["content"]
                for p in ls:
                    if self.args.long is True:
                        self._detailed(p, ls[p])
                    else:
                        print(p)
            else:
                self.print_single(p)
