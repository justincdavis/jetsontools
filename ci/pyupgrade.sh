#!/usr/bin/env bash

find src -name '*.py' -exec pyupgrade {} +
