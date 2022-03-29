import cwlconverter

import argparse, json, yaml, sys

def read_cwl_files(cwl_doc_path, cwl_inputs_object_path=None, debug=False):
    with open(cwl_doc_path, 'r') as f:
        if debug:
            print("Reading CWL from: %s" % cwl_doc_path)
        cwl_doc = yaml.safe_load(f)
    cwl_inputs_object = {}
    if cwl_inputs_object_path is not None:
        if debug:
            print("Reading parameter values from: %s" % cwl_inputs_object_path)
        with open(cwl_inputs_object_path, 'r') as f:
            try:
                cwl_inputs_object = yaml.safe_load(f)
            except:
                with open(cwl_inputs_object_path, 'r') as f2:
                    cwl_inputs_object = json.load(f2)
    return cwl_doc, cwl_inputs_object

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('cwl_document', metavar="cwl_document", help = "Path to a CWL CommandLineTool")
    parser.add_argument('inputs_object', nargs="?", metavar="inputs_object", help = "Path to a YAML or JSON "
        "formatted description of the required input values for the given `cwl_document`.",)
    parser.add_argument('-d', '--debug', action='store_true', help="Debug mode")
    args = parser.parse_args()

    cwl_doc_path = args.cwl_document
    cwl_inputs_object_path = args.inputs_object
    debug = args.debug
    cwl_doc, cwl_inputs_object = read_cwl_files(cwl_doc_path, cwl_inputs_object_path, debug)

    unicore_job, file_list, outputs_list = cwlconverter.convert_cmdline_tool(cwl_doc, cwl_inputs_object, debug=debug)
    print(json.dumps(unicore_job, indent=2, sort_keys = True))

    sys.exit(0)
