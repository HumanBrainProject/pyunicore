#!/usr/bin/env cwltool

cwlVersion: v1.0
class: CommandLineTool
baseCommand: echo
inputs:
  param_1:
    type: string
    inputBinding:
      position: 1
  param_2:
    type: string
    inputBinding:
      position: 2
  param_3:
    type: int
    inputBinding:
      position: 3
  param_4:
    type: int[]
    inputBinding:
      itemSeparator: ","
      position: 4
  param_5:
    type:
      type: array
      items: int
      inputBinding:
        prefix: "-x"
    inputBinding:
      position: 5

outputs: []

stdout: my_out
stderr: my_err
