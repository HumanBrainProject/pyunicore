""" Storage-related commands """

import fnmatch
import os
import pathlib
import re
import sys
from os.path import basename

from pyunicore.cli.base import Base
from pyunicore.client import PathFile
from pyunicore.client import Storage


class IOBase(Base):

    def get_group(self):
        return "Data management"

    def parse_location(self, location: str):
        m = re.match(r"(https://\S+/rest/core/storages/).*", location)
        if m is not None:
            base = m.group(1)
            storage_id = re.match(r"https://\S+/rest/core/storages/(\S+).*", location).group(1)
            tok = storage_id.split("/files")
            storage_id = tok[0]
            path = tok[1] if len(tok) > 1 else "/"
            endpoint = base + storage_id
        else:
            endpoint = None
            path = location
        return endpoint, path


class LS(IOBase):
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

    def _detailed(self, name: str, p: dict):
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
            storage_url, file_path = self.parse_location(endpoint)
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


class CP(IOBase):
    def add_command_args(self):
        self.parser.prog = "unicore cp"
        self.parser.description = self.get_synopsis()
        self.parser.add_argument("source", nargs="+", help="Source(s)")
        self.parser.add_argument("target", help="Target")

    def get_synopsis(self):
        return """Copy files from/to local or UNICORE storages"""

    def get_description(self):
        return "copy files"

    def _download(self, source_endpoint, source_path, target_path):
        storage = Storage(self.credential, storage_url=source_endpoint)
        base_dir, file_pattern = split_path(source_path)
        for fname in crawl_remote(storage, base_dir, file_pattern):
            p = storage.stat(fname)
            have_stdout = False
            if target_path == "-":
                have_stdout = True
                target = os.fdopen(sys.stdout.fileno(), "wb", closefd=False)
            elif os.path.isdir(target_path):
                target = normalized(target_path + "/" + os.path.basename(fname))
            else:
                target = target_path
            self.verbose(f"... {source_endpoint}/files{fname} -> {target}")
            p.download(target)
            if have_stdout:
                target.close()

    def _upload(self, source_path, target_endpoint, target_path):
        storage = Storage(self.credential, storage_url=target_endpoint)
        if target_path.endswith("/"):
            target = normalized(target_path + os.path.basename(source_path))
        else:
            target = normalized(target_path)
        self.verbose(f"... {source_path} -> {target_endpoint}/files{target}")
        storage.upload(source_path, destination=target)

    def run(self, args):
        super().setup(args)
        target_endpoint, target_path = self.parse_location(self.args.target)
        for s in self.args.source:
            source_endpoint, source_path = self.parse_location(s)
            if len(self.args.source) > 1:
                target = target_path + "/" + basename(source_path)
            else:
                target = target_path
                if target.endswith("/"):
                    target = target + basename(source_path)
                if target.endswith("."):
                    target = target + "/" + basename(source_path)
            if source_endpoint is not None:
                self._download(source_endpoint, source_path, target)
            else:
                self._upload(source_path, target_endpoint, target)


def normalized(path: str):
    return pathlib.Path(path).as_posix()


def split_path(path: str):
    pattern = os.path.basename(path)
    base = os.path.dirname(path)
    if len(base) == 0:
        base = "/"
    return base, pattern


def crawl_remote(
    storage: Storage,
    base_dir,
    file_pattern="*",
    recurse=False,
    all=False,
    files_only=True,
    _level=0,
):
    """returns matching paths"""
    if not files_only and _level == 0:
        # return top-level dir because Unix 'find' does it
        bd = storage.stat(base_dir)
        if bd.isdir():
            yield normalized(base_dir)
    file_list = storage.contents(base_dir)["content"]
    for fname in file_list:
        x = file_list[fname]
        if x["isDirectory"] is False or not files_only:
            if not fnmatch.fnmatchcase(os.path.basename(fname), file_pattern):
                continue
            else:
                yield fname
        if x["isDirectory"] and (all or (recurse and fnmatch.fnmatch(fname, file_pattern))):
            yield from crawl_remote(
                storage, base_dir + "/" + fname, file_pattern, recurse, all, _level + 1
            )
