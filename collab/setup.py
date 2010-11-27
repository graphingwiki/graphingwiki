# -*- coding: utf-8 -*-
"""
    @copyright: 2010 by Marko Laakso
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

setup(name='collab', version='$Rev$',
      author='Marko Laakso, Jani Kenttälä',
      author_email='contact@clarifiednetworks.com',
      description='Collab Backend',
      packages=['collabbackend'],
      package_dir={'collabbackend': 'collabbackend'},
      package_data={'collabbackend': ['plugin/*/*.py', 'plugin/__init__.py']},
      data_files=makeDataFiles('share/moin/htdocs', 'htdocs'),
      scripts=[ 'scripts/collab-archive',
        'scripts/collab-account-collablist',
        'scripts/collab-account-create',
        'scripts/collab-account-password',
        'scripts/collab-auth-ejabberd',
        'scripts/collab-create',
        'scripts/collab-htaccess'])
