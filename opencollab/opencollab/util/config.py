# -*- coding: utf-8 -*-
"""
    @copyright: 2008 Lari Huttunen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import sys, copy, optparse, ConfigParser

def parseConfig(config):
    iniopts={}
    configparser = ConfigParser.ConfigParser()
    try:
        configparser.readfp(open(config))
    except IOError:
        error = "ERROR: Cannot read: " + config
        raise IOError(error)
    for section in configparser.sections():
        iniopts[section] = dict(configparser.items(section))
    return iniopts

def parseOptions(specparser, inisection, config=True, category=False, search=False, template=False):
    cliopts = {}
    globalopts = {}
    globalopts[inisection] = {}
    globalopts["creds"] = {}
    creds = set(['url', 'username', 'password'])
    genparser = copy.deepcopy(specparser)
    if config:
        genparser.add_option( "-c", "--config", action="store",
            type="string", dest="config", default=None,
            metavar="CONFIG", help="CONFIG file path.")
    if category:
        genparser.add_option( "-g", "--category", action="store",
            type="string", dest="category", default=None,
            metavar="CATEGORY", help="CATEGORY.")
    if search:
        genparser.add_option( "-s", "--search-string", action="store", 
            type="string", dest="search", default=None,
            metavar="SearchString", help="Metatable() SearchString.")
    if template:
        genparser.add_option( "-t", "--template", action="store", 
            type="string", dest="template", default=None,
            metavar="TEMPLATE", help="Collab TEMPLATE.")
    genparser.add_option( "-u", "--url", action="store", 
        type="string", dest="url", default=None,
        metavar="COLLABURL", help="COLLABURL to connect to.")
    genparser.add_option( "-U", "--username", action="store", 
        type="string", dest="username", default=None,
        metavar="USERNAME", help="USERNAME to use in collab auth.")
    genparser.add_option("-v", "--verbose", action="store_true", 
        dest="verbose", help="Enable verbose output." )
    clivalues, args = genparser.parse_args()
    # Parse arguments
    if args:
        globalopts[inisection]["args"] = args
    else:
        globalopts[inisection]["args"] = []
    # Parse CLI options
    for k,v in vars(clivalues).iteritems():
        cliopts[k] = v
    # Parse config
    if config and clivalues.config:
        try:
            iniopts = parseConfig(clivalues.config)
        except IOError, msg:
            print msg
        else:
            for sect in iniopts:
                if sect == "creds" or sect == inisection:
                    for k,v in iniopts[sect].iteritems():
                        if k in creds and cliopts.get(k) is not None:
                            globalopts[sect][k] = cliopts.get(k)
                        else:
                            globalopts[sect][k] = v
    for c in creds:
        try:
            k = globalopts["creds"][c]
        except KeyError:
            try:
                globalopts["creds"][c] = cliopts.get(c)
            except KeyError:
                globalopts["creds"][c] = None
    # Iterate CLI options
    for k,v in cliopts.iteritems():
        if k in creds:
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
