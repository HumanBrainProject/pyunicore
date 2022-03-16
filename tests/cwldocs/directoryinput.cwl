#!/usr/bin/env cwltool

cwlVersion: v1.0
class: CommandLineTool
baseCommand: test_command
inputs:
  file_1:
    type: Directory
    inputBinding:
      prefix: --input=
      separate: false
      position: 1

outputs: []
