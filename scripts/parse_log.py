#!/usr/bin/env python3

import re
import sys

lines = sys.stdin.readlines()

lines_dicts = []
for line in lines:
    line_dict = {"line": line, "sort_key": 0.0}
    # use pattern matching to extract stat_total_duration
    # m = re.match(r'.*stat_total_duration=(\d+\.\d+)ms.*', line)
    m = re.match(r".*status_code=(\d+) .*", line)
    if m:
        duration = float(m.group(1))
        # print(f'Duration: {duration}')
        line_dict["sort_key"] = duration

    lines_dicts.append(line_dict)

# now sort lines by sort_key
sorted_lines = sorted(lines_dicts, key=lambda line: line["sort_key"])

for line in sorted_lines:
    print("%s: %s" % (line["sort_key"], line["line"].strip()))
    # print(line['line'].strip())
