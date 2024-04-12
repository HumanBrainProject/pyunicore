import os
import unittest
from io import BytesIO
from time import sleep

import pyunicore.client as uc_client
import pyunicore.credentials as uc_credentials


class TestBasic(unittest.TestCase):
    def setUp(self):
        pass

    def get_client(self):
        credential = uc_credentials.UsernamePassword("demouser", "test123")
        base_url = "https://localhost:8080/DEMO-SITE/rest/core"
        transport = uc_client.Transport(credential)
        return uc_client.Client(transport, base_url)

    def get_home_storage(self):
        credential = uc_credentials.UsernamePassword("demouser", "test123")
        transport = uc_client.Transport(credential)
        return uc_client.Storage(
            transport,
            "https://localhost:8080/DEMO-SITE/rest/core/storages/HOME",
        )

    def test_list_storages(self):
        print("*** test_list_storages")
        site_client = self.get_client()
        storages = site_client.get_storages()
        home = None
        for s in storages:
            print(s)
            if "storages/HOME" in s.resource_url:
                home = s
                break
        self.assertIsNotNone(home)
        home.listdir()
        home.listdir(".")
        home.listdir("/")

    def test_upload_download(self):
        print("*** test_upload_download")
        home = self.get_home_storage()
        _path = "tests/integration/files/script.sh"
        _length = os.stat(_path).st_size
        remote_file = home.stat("script.sh")
        with open(_path, "rb") as f:
            remote_file.upload(f)
        self.assertEqual(_length, int(remote_file.properties["size"]))
        _out = BytesIO()
        remote_file.download(_out)
        self.assertEqual(_length, len(str(_out.getvalue(), "UTF-8")))

    def test_upload_download_data(self):
        print("*** test_upload_download_data")
        home = self.get_home_storage()
        _data = "this is some test data"
        _length = len(_data)
        remote_file = home.stat("test.txt")
        remote_file.upload(_data)
        self.assertEqual(_length, int(remote_file.properties["size"]))
        _out = BytesIO()
        remote_file.download(_out)
        self.assertEqual(_length, len(str(_out.getvalue(), "UTF-8")))

    def test_transfer(self):
        print("*** test_transfer")
        storage1 = self.get_home_storage()
        _path = "tests/integration/files/script.sh"
        _length = os.stat(_path).st_size
        with open(_path, "rb") as f:
            storage1.stat("script.sh").upload(f)
        site_client = self.get_client()
        storage2 = site_client.new_job({}).working_dir
        transfer = storage2.receive_file(storage1.resource_url + "/files/script.sh", "script.sh")
        print(transfer)
        while transfer.is_running():
            sleep(2)
        print("Transferred bytes: %s" % transfer.properties["transferredBytes"])
        self.assertEqual(_length, int(transfer.properties["transferredBytes"]))
        transfer2 = storage1.send_file("script.sh", storage2.resource_url + "/files/script2.sh")
        print(transfer2)
        transfer2.poll()
        print("Transferred bytes: %s" % transfer2.properties["transferredBytes"])
        self.assertEqual(_length, int(transfer2.properties["transferredBytes"]))
        for t in site_client.get_transfers():
            print(t)


if __name__ == "__main__":
    unittest.main()
