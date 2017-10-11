#!/bin/bash

export PARENT_DIR=$(cd $(dirname $0); cd ..;pwd)
export PYTHON_BASE=/usr/lib/python2.7
export PYTHONPATH=$PYTHON_BASE/dist-packages:PYTHON_BASE/dist-packages/rtctree/rtmidl:$PARENT_DIR

python FestivalRTC/FestivalRTC.py
