import os
import unittest

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
        home.upload(_path, "script.sh")
        uploaded_file = home.stat("script.sh")
        self.assertEqual(_length, int(uploaded_file.properties["size"]))
        from io import BytesIO

        _out = BytesIO()
        uploaded_file.download(_out)
        self.assertEqual(_length, len(str(_out.getvalue(), "UTF-8")))

    def test_transfer(self):
        print("*** test_transfer")
        storage1 = self.get_home_storage()
        _path = "tests/integration/files/script.sh"
        _length = os.stat(_path).st_size
        storage1.upload(_path, "script.sh")
        site_client = self.get_client()
        storage2 = site_client.new_job({}).working_dir
        transfer = storage2.receive_file(storage1.resource_url + "/files/script.sh", "script.sh")
        print(transfer)
        from time import sleep

        while transfer.is_running():
            sleep(2)
        print("Transferred bytes: %s" % transfer.properties["transferredBytes"])
        self.assertEqual(_length, int(transfer.properties["transferredBytes"]))
        transfer2 = storage1.send_file("script.sh", storage2.resource_url + "/files/script2.sh")
        print(transfer2)
        from time import sleep

        while transfer2.is_running():
            sleep(2)
        print("Transferred bytes: %s" % transfer2.properties["transferredBytes"])
        self.assertEqual(_length, int(transfer2.properties["transferredBytes"]))


if __name__ == "__main__":
    unittest.main()
