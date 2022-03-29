"""
 CWL to UNICORE converter and utilities
"""

def convert_cmdline_tool(cwl_doc, inputs_object = {}, debug = False):
    """ converts a CWL CommandLineTool into a UNICORE JSON job

        Returns: UNICORE JSON job, list of local files to upload,  list of output files
    """
    if cwl_doc['class']!="CommandLineTool":
        raise Exception("Unsupported 'class' of CWL document, must be 'CommandLineTool'")
    unicore_job = {}

    _hints = cwl_doc.get("hints", {})

    _is_container = _hints.get("DockerRequirement") is not None
    if debug:
        print("Container mode: %s" % _is_container)

    if _is_container:
        unicore_job['ApplicationName'] = "CONTAINER"
        docker_image = _hints['DockerRequirement']['dockerPull']
        run_options = [ "--contain", "--ipc", "--bind $PWD", "--pwd $PWD"]
        params = {'IMAGE_URL': docker_image,
                  'COMMAND': cwl_doc['baseCommand'],
                  'RUN_OPTS': " ".join(run_options)
                  }
        unicore_job['Parameters'] = params
    else:
        unicore_job['Executable'] = cwl_doc['baseCommand']

    unicore_job["Arguments"] = build_argument_list(cwl_doc.get("inputs", {}), inputs_object, debug)
    files = get_file_list(inputs_object)
    outputs = []

    return unicore_job, files, outputs

def build_argument_list(cwl_inputs, inputs_object = {}, debug = False):
    """ generate the argument list from the CWL inputs and an inputs_object containing values """
    render = {}
    for i in cwl_inputs:
        input_item = cwl_inputs[i]
        input_binding = input_item.get("inputBinding", None)
        if input_binding is not None:
            pos = int(input_binding['position'])
            value = render_value(i, input_item, inputs_object)
            if value is not None:
                render[pos] = value
    args = []
    for index, value in sorted(render.items(), key = lambda x: x[0]):
        args.append(value)
    return args

def render_value(name, input_spec, inputs_object={}):
    """ generate a concrete value for command-line argument """
    value = inputs_object.get(name, None)
    parameter_type = input_spec.get("type", "string")
    if parameter_type.endswith("?"):
        parameter_type = parameter_type[:-1]
        if value is None:
            return None
    elif value is None:
        raise Exception("Parameter value for parameter '%s' is missing in inputs object" % name)
    input_binding = input_spec.get("inputBinding", {})
    prefix = input_binding.get("prefix", "")
    if prefix!="" and input_binding.get("separate", True) is True:
        prefix = prefix + " "

    if parameter_type=="boolean":
        if value=="true":
            result = prefix
    elif parameter_type=="File" or parameter_type=="Directory":
        result = prefix+value['path']
    else:
        result = prefix + str(value)

    return result

def get_file_list(inputs_object={}):
    file_list = []
    for x in inputs_object:
        input_item = inputs_object[x]
        try:
            if input_item.get("class", None)=="File":
                file_list.append(input_item['path'])
            elif input_item.get("class", None)=="Directory":
                # TBD resolve
                pass
        except:
            pass
    return file_list
