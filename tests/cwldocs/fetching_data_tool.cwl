#!/usr/bin/env cwltool

cwlVersion: v1.0
class: CommandLineTool
baseCommand: echo
hints:
  DockerRequirement:
    dockerPull: docker-registry.ebrains.eu/tc/cwl-workflows/psd_workflow_fetching_data:latest
  ResourceRequirement:
    ramMin: 2048
    outdirMin: 4096
inputs:
  bucket_id:
    type: string
    inputBinding:
      position: 1
  object_name:
    type: string
    inputBinding:
      position: 2
  token:
    type: string
    inputBinding:
      position: 3
outputs:
  fetched_file:
    type: File
    outputBinding:
      glob: $(inputs.object_name)
