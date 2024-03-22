"""
 CWL to UNICORE converter and utilities
"""


def convert_cmdline_tool(cwl_doc, inputs_object={}, debug=False):
    """converts a CWL CommandLineTool into a UNICORE JSON job

    Returns: UNICORE JSON job, list of local files to upload,  list of output files
    """
    if cwl_doc["class"] != "CommandLineTool":
        raise ValueError("Unsupported 'class' of CWL document, must be 'CommandLineTool'")
    unicore_job = {}

    _hints = cwl_doc.get("hints", {})

    _is_container = _hints.get("DockerRequirement") is not None
    if debug:
        print("Container mode: %s" % _is_container)

    if _is_container:
        unicore_job["ApplicationName"] = "CONTAINER"
        docker_image = _hints["DockerRequirement"]["dockerPull"]
        params = {
            "IMAGE_URL": docker_image,
            "COMMAND": cwl_doc["baseCommand"],
        }
        unicore_job["Parameters"] = params
    else:
        unicore_job["Executable"] = cwl_doc["baseCommand"]

    unicore_job["Arguments"] = build_argument_list(cwl_doc.get("inputs", {}), inputs_object, debug)

    if "stdout" in cwl_doc.keys():
        unicore_job["Stdout"] = cwl_doc["stdout"]
    if "stderr" in cwl_doc.keys():
        unicore_job["Stderr"] = cwl_doc["stderr"]
    if "stdin" in cwl_doc.keys():
        unicore_job["Stdin"] = cwl_doc["stdin"]

    remote_files = get_remote_file_list(inputs_object)
    if len(remote_files) > 0:
        unicore_job["Imports"] = remote_files
    files = get_local_file_list(inputs_object)
    outputs = []

    return unicore_job, files, outputs


def build_argument_list(cwl_inputs, inputs_object={}, debug=False):
    """generate the argument list from the CWL inputs and an inputs_object containing values"""
    render = {}
    for i in cwl_inputs:
        input_item = cwl_inputs[i]
        input_binding = input_item.get("inputBinding", None)
        if input_binding is not None:
            pos = int(input_binding["position"])
            value = render_value(i, input_item, inputs_object)
            if value is not None:
                render[pos] = value
    args = []
    for _, value in sorted(render.items(), key=lambda x: x[0]):
        for x in value:
            args.append(x)
    return args


def render_value(name, input_spec, inputs_object={}):
    """generate a concrete value for command-line argument"""
    value = inputs_object.get(name, None)
    parameter_type = input_spec["type"]
    input_binding = input_spec.get("inputBinding", {})

    is_array = False
    is_nested_array = False

    if isinstance(parameter_type, dict):
        is_array = True
        is_nested_array = True
        input_binding = parameter_type.get("inputBinding", {})
        parameter_type = parameter_type["items"]
    elif parameter_type.endswith("[]"):
        is_array = True
        parameter_type = parameter_type[:-2]

    prefix = input_binding.get("prefix", "")
    item_separator = input_binding.get("itemSeparator", None)
    separate = prefix != "" and input_binding.get("separate", True)

    if parameter_type.endswith("?"):
        parameter_type = parameter_type[:-1]
        if value is None:
            return None
    elif value is None:
        raise TypeError("Parameter value for parameter '%s' is missing in inputs object" % name)

    if parameter_type == "boolean":
        if (isinstance(value, bool) and value) or value == "true":
            return prefix
        else:
            return None

    if is_array:
        if not isinstance(value, list):
            raise ValueError(
                "Parameter '{}' is declared as 'array of {}', but value is not a list".format(
                    name, parameter_type
                )
            )
        values = value
    else:
        values = [value]

    resolved_values = []

    for v in values:
        if parameter_type == "string" and " " in v:
            current_value = '"' + v + '"'
        elif parameter_type == "File" or parameter_type == "Directory":
            current_value = get_filename_in_jobdir(v)
        else:
            current_value = str(v)
        resolved_values.append(current_value)

    if item_separator is not None:
        resolved_values = [item_separator.join(resolved_values)]

    first = True
    result = []
    for v in resolved_values:
        if first:
            if prefix != "":
                if not separate:
                    result.append(prefix + v)
                else:
                    result.append(prefix)
                    result.append(v)
            else:
                result.append(v)
        else:
            if prefix != "":
                if not separate:
                    result.append(prefix + v)
                else:
                    if is_nested_array:
                        result.append(prefix)
                    result.append(v)
            else:
                result.append(v)
        first = False

    return result


def get_local_file_list(inputs_object={}):
    file_list = []
    for x in inputs_object:
        input_item = inputs_object[x]
        try:
            if input_item.get("class", None) == "File":
                path = input_item.get("path", None)
                if path is None:
                    path = input_item.get("location", "")
                    if not path.startswith("file:"):
                        continue
                    path = path[5:]
                file_list.append(path)
            elif input_item.get("class", None) == "Directory":
                # TBD resolve
                pass
        except AttributeError:
            pass
    return file_list


def get_remote_file_list(inputs_object={}):
    file_list = []
    for x in inputs_object:
        input_item = inputs_object[x]
        try:
            if input_item.get("class", None) == "File":
                path = input_item.get("path", None)
                if path is not None:
                    continue
                path = input_item.get("location")
                if path.startswith("file:"):
                    continue
                base_name = input_item.get("basename", None)
                if base_name is None:
                    base_name = path.split("/")[-1]
                file_list.append({"From": path, "To": base_name})
        except AttributeError:
            pass
    return file_list


def get_filename_in_jobdir(input_item):
    name = input_item.get("path", None)
    if name is None:
        name = input_item.get("basename", None)
    if name is None:
        name = input_item.get("location").split("/")[-1]
    return name
