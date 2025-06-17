#!/usr/bin/env bash
python -m jetsontools profile --output data/logs/$1.tegrastats --interval 5 --readall --sudo --command sleep 1
