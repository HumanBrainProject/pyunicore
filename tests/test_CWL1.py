import json, unittest

import cwlconverter, cwltool

class TestCWL1(unittest.TestCase):
    def setUp(self):
        pass

    def test_convert_echo(self):
        print("*** test_convert_echo")
        cwl_doc, cwl_input_object = cwltool.read_cwl_files("tests/cwldocs/echo.cwl", "tests/cwldocs/echo.params") 
        u_job, files, outputs = cwlconverter.convert_cmdline_tool(cwl_doc, cwl_input_object)
        print(json.dumps(u_job, indent=2))
        self.assertEqual("echo", u_job['Executable'])
        self.assertEqual('"hello world!"', u_job['Arguments'][0])
        self.assertEqual("two", u_job['Arguments'][1])
        self.assertEqual("42", u_job['Arguments'][2])
        self.assertEqual("1,2,3", u_job['Arguments'][3])
        self.assertEqual(["-x", "7","-x","8"], u_job['Arguments'][4:9])
        self.assertEqual("my_out", u_job['Stdout'])
        self.assertEqual("my_err", u_job['Stderr'])
        self.assertEqual(0, len(files))
 
    def test_convert_fileparam(self):
        print("*** test_convert_fileparam")
        cwl_doc, cwl_input_object = cwltool.read_cwl_files("tests/cwldocs/fileinput.cwl", "tests/cwldocs/fileinput.params") 
        u_job, files, outputs = cwlconverter.convert_cmdline_tool(cwl_doc, cwl_input_object)
        print(json.dumps(u_job, indent=2))
        self.assertEqual("--file1=test.sh", u_job['Arguments'][0])
        self.assertEqual(["--file2", "file2"], u_job['Arguments'][1:3])
        self.assertEqual(2, len(files))
        self.assertTrue("test.sh" in files)
        self.assertTrue("file2" in files)
    
    def test_convert_fileparam_with_remotes(self):
        print("*** test_convert_fileparam_with_remotes")
        cwl_doc, cwl_input_object = cwltool.read_cwl_files("tests/cwldocs/fileinput_remote.cwl", 
                                                           "tests/cwldocs/fileinput_remote.params") 
        u_job, files, outputs = cwlconverter.convert_cmdline_tool(cwl_doc, cwl_input_object)
        print(json.dumps(u_job, indent=2))
        self.assertEqual("--file1=test.sh", u_job['Arguments'][0])
        self.assertEqual(["--file2", "file2"], u_job['Arguments'][1:3])
        self.assertEqual("some_remote_file", u_job['Arguments'][3])
        self.assertEqual("file.txt", u_job['Arguments'][4])
        self.assertEqual(2, len(files))
        self.assertTrue("test.sh" in files)
        self.assertTrue("file2" in files)
        remotes = u_job["Imports"]
        self.assertEqual(2, len(remotes))
        print(json.dumps(u_job, indent=2))

    def test_handle_directory_param(self):
        print("*** test_handle_directory_param")
        cwl_doc, cwl_input_object = cwltool.read_cwl_files("tests/cwldocs/directoryinput.cwl", "tests/cwldocs/directoryinput.params") 
        u_job, files, outputs = cwlconverter.convert_cmdline_tool(cwl_doc, cwl_input_object)
        self.assertEqual("--input=tests/cwldocs", u_job['Arguments'][0])
        self.assertEqual(1, len(files))

    def test_convert_array_inputs(self):
        print("*** test_convert_array_inputs")
        cwl_doc, cwl_input_object = cwltool.read_cwl_files("tests/cwldocs/array-inputs.cwl", "tests/cwldocs/array-inputs.params") 
        u_job, files, outputs = cwlconverter.convert_cmdline_tool(cwl_doc, cwl_input_object)
        print(json.dumps(u_job, indent=2))
        args = u_job["Arguments"]
        self.assertEqual(8, len(args))
        self.assertEqual(["-A", "one", "two", "three"], args[0:4])
        self.assertEqual(["-B=four", "-B=five", "-B=six"], args[4:7])
        self.assertEqual("-C=seven,eight,nine", args[7])

    def test_resolve_input_files(self):
        print("*** test_resolve_input_files")        
        pass
    
if __name__ == '__main__':
    unittest.main()
