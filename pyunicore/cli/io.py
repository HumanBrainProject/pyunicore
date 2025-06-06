from __future__ import annotations

import fnmatch
import os
import pathlib
import re
import sys
from os.path import basename
from urllib.parse import urlparse

from pyunicore.cli.base import Base
from pyunicore.client import PathFile
from pyunicore.client import Storage
from pyunicore.client import Transfer


class IOBase(Base):
    """Base class for storage related commands"""

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
    """List remote directories"""

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
    """Copy file(s)"""

    def add_command_args(self):
        self.parser.prog = "unicore cp"
        self.parser.description = self.get_synopsis()
        self.parser.add_argument("source", nargs="+", help="Source(s)")
        self.parser.add_argument("target", help="Target")
        self.parser.add_argument(
            "-E",
            "--extra-parameters",
            required=False,
            type=str,
            help="Additional settings for the transfer (key1=val1,key2=val2)",
        )
        self.parser.add_argument(
            "-a",
            "--asynchronous",
            required=False,
            action="store_true",
            help="(server-server only) Asynchronous mode, don't wait for transfer to finish",
        )

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
                target = normalized(target_path + "/" + basename(fname))
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

    def _stage_in(self, source_url, target_endpoint, target_path, params={}):
        storage = Storage(self.credential, storage_url=target_endpoint)
        if target_path.endswith("/"):
            source_path = urlparse(source_url).path
            target = normalized(target_path + os.path.basename(source_path))
        else:
            target = normalized(target_path)
        self.verbose(f"... {source_url} -> {target_endpoint}: {target}")
        return storage.receive_file(
            remote_url=source_url, file_name=target, additional_parameters=params
        )

    def _stage_out(self, source_endpoint, source_path, target_url, params={}):
        storage = Storage(self.credential, storage_url=source_endpoint)
        self.verbose(f"... {source_endpoint}: {source_path} -> {target_url}")
        return storage.send_file(
            remote_url=target_url, file_name=source_path, additional_parameters=params
        )

    def _is_remote(self, location):
        return re.match(r"([-a-z0-9]*:)?(http[s]?)?://(.*)", location.lower()) is not None

    def _parse_extra_params(self, param_spec: str):
        res = {}
        if param_spec:
            for kv in param_spec.split(","):
                k, v = kv.split("=", 1)
                res[k] = v
        return res

    def run(self, args):
        super().setup(args)
        params = self._parse_extra_params(self.args.extra_parameters)
        target_endpoint, target_path = self.parse_location(self.args.target)
        controller: Transfer = None
        for s in self.args.source:
            source_endpoint, source_path = self.parse_location(s)
            if source_endpoint is not None:
                if self._is_remote(self.args.target):
                    controller = self._stage_out(
                        source_endpoint, source_path, self.args.target, params
                    )
                else:
                    self._download(source_endpoint, source_path, target_path)
            elif target_endpoint is not None:
                if self._is_remote(s):
                    controller = self._stage_in(s, target_endpoint, target_path, params)
            else:
                print(f"Cannot process: {s}->{self.args.target}")
        if controller:
            if self.args.asynchronous:
                print(controller.resource_url)
            else:
                self.verbose(f"Waiting for transfer {controller.resource_url} to finish...")
                controller.poll()


class Cat(IOBase):
    """Print a remote file to standard output"""

    def add_command_args(self):
        self.parser.prog = "unicore cat"
        self.parser.description = self.get_synopsis()
        self.parser.add_argument("source", nargs="+", help="Source(s)")

    def get_synopsis(self):
        return """Prints remote file(s) to standard output"""

    def get_description(self):
        return "cat remote files"

    def _cat(self, source_endpoint, source_path):
        storage = Storage(self.credential, storage_url=source_endpoint)
        base_dir, file_pattern = split_path(source_path)
        for fname in crawl_remote(storage, base_dir, file_pattern):
            p = storage.stat(fname)
            target = os.fdopen(sys.stdout.fileno(), "wb", closefd=False)
            self.verbose(f"... {source_endpoint}/files{fname}")
            p.download(target)
            target.close()

    def run(self, args):
        super().setup(args)
        for s in self.args.source:
            source_endpoint, source_path = self.parse_location(s)
            if source_endpoint is not None:
                self._cat(source_endpoint, source_path)
            else:
                raise ValueError("Not a remote UNICORE file: %s" % s)


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
