# -*- coding: utf-8 -*-
"""
    @copyright: 2010 by Marko Laakso
    @license: GNU GPL <http://www.gnu.org/licenses/gpl.html>
"""

import os
import errno
from distutils.core import setup
from distutils.util import convert_path
from distutils.dir_util import remove_tree
from distutils.command.build import build
from distutils.command.install import install


# Helpers copied from MoinMoin setup.py (http://moinmo.in)

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


# Real action

def rmtree(path):
    try:
        remove_tree(convert_path(path))
    except OSError, err:
        if err.errno != errno.ENOENT:
            raise


class RemovingBuild(build):
    def run(self):
        rmtree(self.build_lib)
        rmtree(self.build_scripts)

        build.run(self)


class RemovingInstall(install):
    def run(self):
        build_py = self.distribution.get_command_obj("build_py")
        if self.distribution.packages:
            for package in self.distribution.packages:
                package_dir = build_py.get_package_dir(package)
                rmtree(os.path.join(self.install_lib, package_dir))
        install.run(self)

setup(
    name='collab',
    version='1.0',
    author='Marko Laakso, Jani Kenttälä',
    author_email='contact@clarifiednetworks.com',
    description='Collab Backend',
    packages=[
        'collabbackend',
        'collabbackend.plugin',
        'collabbackend.plugin.action',
        'collabbackend.plugin.macro',
        'collabbackend.plugin.theme',
        'collabbackend.plugin.xmlrpc'
    ],
    data_files=makeDataFiles('share/moin/htdocs', 'htdocs'),
    scripts=[
        'scripts/collab-account-collablist',
        'scripts/collab-account-create',
        'scripts/collab-account-notify',
        'scripts/collab-account-password',
        'scripts/collab-account-remove',
        'scripts/collab-account-rename',
        'scripts/collab-archive',
        'scripts/collab-auth-ejabberd',
        'scripts/collab-check',
        'scripts/collab-create',
        'scripts/collab-group-edit',
        'scripts/collab-group-list',
        'scripts/collab-htaccess',
    ],
    cmdclass={
        "build": RemovingBuild,
        "install": RemovingInstall
    }
)
