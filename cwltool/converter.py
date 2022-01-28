"""
 CWL to UNICORE converter and utilities
"""

def convert_cmdline_tool(cwl_doc, inputs_object = {}, debug = False):
    """ converts a CWL CommandLineTool into a UNICORE JSON job """
    if cwl_doc['class']!="CommandLineTool":
        raise Exception("Unsupported 'class' of CWL document, must be 'CommandLineTool'")
    unicore_job = {}

    _hints = cwl_doc.get("hints", {})

    _is_container = _hints.get("DockerRequirement") is not None
    if debug:
        print("Container mode: %s" % _is_container)

    if _is_container:
        docker_image = _hints['DockerRequirement']['dockerPull']
        params = {'IMAGE_URL': docker_image,
                  'COMMAND': cwl_doc['baseCommand']
                  }
        unicore_job['Parameters'] = params
        unicore_job['ApplicationName'] = "CONTAINER"
    else:
        unicore_job['Executable'] = cwl_doc['baseCommand']

    unicore_job["Arguments"] = build_argument_list(cwl_doc.get("inputs", {}), inputs_object, debug)

    return unicore_job

def build_argument_list(cwl_inputs, inputs_object = {}, debug = False):
    """ generate the argument list from the CWL inputs and an inputs_object containing values """
    render = {}
    for i in cwl_inputs:
        input = cwl_inputs[i]
        input_binding = input.get("inputBinding", None)
        if input_binding is not None:
            pos = int(input_binding['position'])
            value = render_value(i, input, inputs_object)
            if value is not None:
                render[pos] = value
    args = []
    for index, value in sorted(render.items(), key = lambda x: x[0]):
        args.append(value)
    return args

def render_value(name, input_spec, inputs_object={}):
    """ generate a concrete value for command-line argument """
    type = input_spec.get("type", "string")
    optional = False
    prefix = input_spec.get("prefix", "")
    value = inputs_object.get(name, None)
    result = None
    if input_spec.get("separate", "true")=="true":
        prefix = prefix + " "
    
    if type.endswith("?"):
        type = type[:-1]
        optional = True
    
    if value is None:
        if optional:
            return None
        else:
            raise Exception("Parameter value for parameter '%s' is missing in inputs object" % name)
    
    if type=="boolean":
        if value=="true":
            result = prefix
    else:
        result = prefix + str(value)
        
    return result

    