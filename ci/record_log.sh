#!/usr/bin/env bash
mkdir -p data/logs/$1
python3 -m jetsontools profile --output data/logs/$1/all.tegrastats --interval 5 --readall --sudo --command sleep 1
python3 -m jetsontools profile --output data/logs/$1/basic.tegrastats --interval 5 --command sleep 1
