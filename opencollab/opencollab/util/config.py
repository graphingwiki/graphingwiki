# -*- coding: utf-8 -*-
"""
    @copyright: 2008 Lari Huttunen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import sys, copy, optparse, ConfigParser

def parseConfig(config, *sections):
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

def parseOptions(specparser, inisection, config=True, category=False, template=False):
    cliopts = {}
    globalopts = {}
    globalopts[inisection] = {}
    globalopts["creds"] = {}
    genparser = copy.deepcopy(specparser)
    if config:
        genparser.add_option( "-c", "--config", action="store",
            type="string", dest="config", default=None,
            metavar="CONFIG", help="CONFIG file path.")
    if category:
        genparser.add_option( "-g", "--category", action="store",
            type="string", dest="category", default=None,
            metavar="CONFIG", help="CONFIG file path.")
    if template:
        genparser.add_option( "-t", "--template", action="store", 
            type="string", dest="template", default=None,
            metavar="TEMPLATE", help="Collab TEMPLATE.")
    genparser.add_option( "-u", "--url", action="store", 
        type="string", dest="url", default=None,
        metavar="COLLABURL", help="COLLABURL to connect to.")
    genparser.add_option("-v", "--verbose", action="store_true", 
        dest="verbose", default=False, help="Enable verbose output." )
    genparser.set_usage("%prog [options]")
    clivalues, args = genparser.parse_args()
    # Parse arguments
    if args:
        globalopts[inisection]["args"] = args
    else:
        globalopts[inisection]["args"] = None
    # Parse CLI options
    for k,v in vars(clivalues).iteritems():
        cliopts[k] = v
    # Parse config
    if config and clivalues.config:
        iniopts = parseConfig(clivalues.config, "creds", inisection)
        for iopt in iniopts:
            globalopts[iopt] = iniopts[iopt]
    try: 
        globalopts["creds"]["url"] = cliopts.get("url")
    except (AttributeError, KeyError):
        try:
            globalopts["creds"]["url"]
        except KeyError:
            globalopts["creds"]["url"] = None
    # Iterate CLI options
    for k,v in cliopts.iteritems():
        if k == "url":
            pass
        else:
            try: 
                globalopts[inisection][k]
            except KeyError:
                globalopts[inisection][k] = v
            else:
                if v is not None:
                    globalopts[inisection][k] = v
    return globalopts
