# -*- coding: utf-8 -*-

import sys
import ConfigParser

def parse_config(config, *sections):
    iopts={}
    configparser = ConfigParser.ConfigParser()
    try:
        configparser.readfp(open(config))
    except IOError:
	error = "Configuration file: \"" + config + "\" doesn't exist."
        sys.exit(error)
    for section in configparser.sections():
        iopts[section] = dict(configparser.items(section))
    for section in sections:
        if section not in iopts:
            iopts[section] = section
    return iopts

