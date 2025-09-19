import os
import unittest
from io import BytesIO

import aiofiles

import pyunicore.aio.client as uc_client
import pyunicore.credentials as uc_credentials


class TestAsyncStorage(unittest.IsolatedAsyncioTestCase):
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

    async def test_list_storages(self):
        print("*** test_list_storages")
        async with self.get_client() as site_client:
            storages = await site_client.get_storages()
            home = None
            for s in storages:
                print(s)
                if "storages/HOME" in s.resource_url:
                    home = s
                    break
            self.assertIsNotNone(home)
            await home.listdir()
            await home.listdir(".")
            await home.listdir("/")

    async def test_upload_download(self):
        print("*** test_upload_download")
        async with self.get_home_storage() as home:
            _path = "tests/integration/files/script.sh"
            _length = os.stat(_path).st_size
            async with aiofiles.open(_path, "rb") as f:
                await home.put(f, "script.sh")
            remote_file = await home.stat("script.sh")
            self.assertEqual(_length, await remote_file.size)
            _out = BytesIO()
            await remote_file.download(_out)
            self.assertEqual(_length, len(str(_out.getvalue(), "UTF-8")))

    async def test_upload_download_data(self):
        print("*** test_upload_download_data")
        async with self.get_home_storage() as home:
            _data = "this is some test data"
            _length = len(_data)
            await home.put(_data, "test.txt")
            remote_file = await home.stat("test.txt")
            self.assertEqual(_length, await remote_file.size)
            _out = BytesIO()
            await remote_file.download(_out)
            self.assertEqual(_length, len(str(_out.getvalue(), "UTF-8")))

    async def test_transfer(self):
        print("*** test_transfer")
        async with self.get_home_storage() as storage1:
            _path = "tests/integration/files/script.sh"
            _length = os.stat(_path).st_size
            async with aiofiles.open(_path, "rb") as f:
                await storage1.put(f, "script.sh")
            async with self.get_client() as site_client:
                j = await site_client.new_job({})
                storage2 = await j.working_dir
                await storage2._wait_until_ready()
                transfer = await storage2.receive_file(
                    storage1.resource_url + "/files/script.sh", "script.sh"
                )
                print(transfer)
                await transfer.poll()
                self.assertFalse(await transfer.is_running)
                n = await transfer.transferred_bytes
                print("Transferred bytes: %s" % n)
                self.assertEqual(_length, n)

                transfer2 = await storage1.send_file(
                    "script.sh", storage2.resource_url + "/files/script2.sh"
                )
                print(transfer2)
                await transfer2.poll()
                n2 = await transfer2.transferred_bytes
                print("Transferred bytes: %s" % n2)
                self.assertEqual(_length, n2)
                for t in await site_client.get_transfers():
                    print(t)


if __name__ == "__main__":
    unittest.main()
