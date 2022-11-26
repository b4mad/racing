#!/usr/bin/env python3

import os
import glob
import logging


import daiquiri


from history import History


daiquiri.setup(level=logging.INFO)
_LOGGER = logging.getLogger("utils")


if __name__ == "__main__":
    filters = []

    if os.getenv("DEBUG", "1") == "1":
        _LOGGER.setLevel(logging.DEBUG)
        _LOGGER.debug("Debug mode enabled")

    _LOGGER.info("validating CSV files...")

    dir_path = os.path.dirname(os.path.realpath(__file__))
    for candidate_files in glob.glob(dir_path + "/*-*.csv"):
        c, t = candidate_files.split("-")
        carmodel = c.split("/")[-1]
        trackcode = t.split(".")[0]

        filters.append(
            {
                "TrackCode": trackcode,
                "CarModel": carmodel,
            },
        )

    for filter in filters:
        _LOGGER.info(f"reading {filter['CarModel']}-{filter['TrackCode']}")
        history = History()
        history.set_filter(filter)
        history.init_brakepoints()
