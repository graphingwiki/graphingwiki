# -*- coding: utf-8 -*-
"""
    @copyright: 2005-2011 by Juhani Eronen, Marko Laakso
    @license: GNU GPL <http://www.gnu.org/licenses/gpl.html>
"""

import os
from distutils.core import setup

## Helpers copied from MoinMoin setup.py (http://moinmo.in)

def isbad(name):
    """ Whether name should not be installed """
    return (name.startswith('.') or
            name.startswith('#') or
            name.endswith('.pickle') or
            name == 'CVS')

def isgood(name):
    """ Whether name should be installed """
    return not isbad(name)

def makeDataFiles(prefix, dir):
    """ Create distutils data_files structure from dir  """
    # Strip 'dir/' from of path before joining with prefix
    dir = dir.rstrip('/')
    strip = len(dir) + 1
    found = []
    os.path.walk(dir, visit, (prefix, strip, found))
    return found

def visit((prefix, strip, found), dirname, names):
    """ Visit directory, create distutil tuple

    Add distutil tuple for each directory using this format:
        (destination, [dirname/file1, dirname/file2, ...])

    distutil will copy later file1, file2, ... info destination.
    """
    files = []
    # Iterate over a copy of names, modify names
    for name in names[:]:
        path = os.path.join(dirname, name)
        # Ignore directories -  we will visit later
        if os.path.isdir(path):
            # Remove directories we don't want to visit later
            if isbad(name):
                names.remove(name)
            continue
        elif isgood(name):
            files.append(path)
    destination = os.path.join(prefix, dirname[strip:])
    found.append((destination, files))

## Real action

old_plugins = {'action': ['ShowProcessGraph.py', 'MetaCSV.py', 'metaCVS.py',
                          'ShowGraphIE.py', 'MetaTableEdit.py',
                          'ShowLatexSource.py', 'metaRadarDiagram.py',
                          'metaeditform.py', 'ShowGraphSimple.py'],
               'macro': ['metaRadarDiagram.py'],
               'script': ['scripts/gwiki-debuggraph', 'scripts/moin-showpage', 
                          'scripts/moin-editpage']}

setup(name='graphingwiki', version='0.1',
      author='Juhani Eronen, Joachim Viide, Erno Kuusela, Aki Helin',
      author_email='exec@iki.fi',
      description='Graphingwiki - Semantic extension for MoinMoin',
      packages=['graphingwiki'],
      package_dir={'graphingwiki': 'graphingwiki'},
      package_data={'graphingwiki': ['plugin/*/*.py', 'backend/*.py',
                                     'world_map.png', "plugin/__init__.py"]},
      data_files=makeDataFiles('share/moin/htdocs', 'htdocs'),      
      scripts=['scripts/gwiki-rehash', 'scripts/gwiki-showgraph',
               'scripts/gwiki-showpage', 'scripts/mm2gwiki.py', 
               'scripts/gwiki-editpage', 'scripts/gwiki-get-tgz'])
