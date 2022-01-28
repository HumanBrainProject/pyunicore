#!/usr/bin/env cwltool

cwlVersion: v1.0
class: CommandLineTool
baseCommand: echo
inputs:
  echo_line:
    type: string
    inputBinding:
      position: 1

outputs: []
