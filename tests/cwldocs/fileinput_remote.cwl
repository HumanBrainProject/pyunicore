#!/usr/bin/env cwltool

cwlVersion: v1.0
class: CommandLineTool
baseCommand: test_command
inputs:
  file_1:
    type: File
    inputBinding:
      prefix: --file1=
      separate: false
      position: 1
  file_2:
    type: File
    inputBinding:
      prefix: --file2
      separate: true
      position: 2

outputs: []
