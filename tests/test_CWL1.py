import json, unittest

import cwlconverter, cwltool

class TestCWL1(unittest.TestCase):
    def setUp(self):
        pass

    def test_convert_echo(self):
        print("*** test_convert_echo")
        cwl_doc, cwl_input_object = cwltool.read_cwl_files("tests/cwldocs/echo.cwl", "tests/cwldocs/echo.params") 
        u_job, files, outputs = cwlconverter.convert_cmdline_tool(cwl_doc, cwl_input_object)
        self.assertEqual("echo", u_job['Executable'])
        self.assertEqual("hello world!", u_job['Arguments'][0])
        self.assertEqual(0, len(files))

    def test_convert_fileparam(self):
        print("*** test_convert_fileparam")
        cwl_doc, cwl_input_object = cwltool.read_cwl_files("tests/cwldocs/fileinput.cwl", "tests/cwldocs/fileinput.params") 
        u_job, files, outputs = cwlconverter.convert_cmdline_tool(cwl_doc, cwl_input_object)
        self.assertEqual("--file1=test.sh", u_job['Arguments'][0])
        self.assertEqual("--file2 file2", u_job['Arguments'][1])
        self.assertEqual(2, len(files))
        self.assertTrue("test.sh" in files)
        self.assertTrue("file2" in files)
    
    def test_convert_fileparam_with_remotes(self):
        print("*** test_convert_fileparam_with_remotes")
        cwl_doc, cwl_input_object = cwltool.read_cwl_files("tests/cwldocs/fileinput_remote.cwl", 
                                                           "tests/cwldocs/fileinput_remote.params") 
        u_job, files, outputs = cwlconverter.convert_cmdline_tool(cwl_doc, cwl_input_object)
        self.assertEqual("--file1=test.sh", u_job['Arguments'][0])
        self.assertEqual("--file2 file2", u_job['Arguments'][1])
        self.assertEqual(2, len(files))
        self.assertTrue("test.sh" in files)
        self.assertTrue("file2" in files)
        remotes = u_job["Imports"]
        self.assertEqual(2, len(remotes))
        print(u_job)

    def test_handle_directory_param(self):
        print("*** test_handle_directory_param")
        cwl_doc, cwl_input_object = cwltool.read_cwl_files("tests/cwldocs/directoryinput.cwl", "tests/cwldocs/directoryinput.params") 
        u_job, files, outputs = cwlconverter.convert_cmdline_tool(cwl_doc, cwl_input_object)
        self.assertEqual("--input=tests/cwldocs", u_job['Arguments'][0])
        self.assertEqual(1, len(files))

    def test_resolve_input_files(self):
        print("*** test_resolve_input_files")        
        pass
    
if __name__ == '__main__':
    unittest.main()
