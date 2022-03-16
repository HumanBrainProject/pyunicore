import json, unittest

import cwlconverter, cwltool

class TestCWL1(unittest.TestCase):
    def setUp(self):
        pass

    def test_convert_echo(self):
        cwl_doc, cwl_input_object = cwltool.read_cwl_files("tests/cwldocs/echo.cwl", "tests/cwldocs/echo.params") 
        u_job, files = cwlconverter.convert_cmdline_tool(cwl_doc, cwl_input_object)
        self.assertEqual("echo", u_job['Executable'])
        self.assertEqual("hello world!", u_job['Arguments'][0])
        self.assertEqual(0, len(files))

    def test_convert_fileparam(self):
        cwl_doc, cwl_input_object = cwltool.read_cwl_files("tests/cwldocs/fileinput.cwl", "tests/cwldocs/fileinput.params") 
        u_job, files = cwlconverter.convert_cmdline_tool(cwl_doc, cwl_input_object)
        self.assertEqual("--file1=test.sh", u_job['Arguments'][0])
        self.assertEqual("--file2 file2", u_job['Arguments'][1])
        self.assertEqual(2, len(files))
        self.assertTrue("test.sh" in files)
        self.assertTrue("file2" in files)
        
    def test_handle_directory_param(self):
        cwl_doc, cwl_input_object = cwltool.read_cwl_files("tests/cwldocs/directoryinput.cwl", "tests/cwldocs/directoryinput.params") 
        u_job, files = cwlconverter.convert_cmdline_tool(cwl_doc, cwl_input_object)
        self.assertEqual("--file1=test.sh", u_job['Arguments'][0])
        self.assertEqual("--file2 file2", u_job['Arguments'][1])
        self.assertEqual(2, len(files))
        self.assertTrue("test.sh" in files)
        self.assertTrue("file2" in files)

    def test_resolve_input_files(self):
        pass

if __name__ == '__main__':
    unittest.main()
