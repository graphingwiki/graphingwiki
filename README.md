# GraphingWiki

This is the GraphingWiki MoinMoin extension. 

Note: Only MoinMoin versions 1.8+ supported.

## Install

For more thorough installation instructions and administrative scripts, please
refer to the documentation in the [Collab
Backend](https://github.com/graphingwiki/collabbackend) repository.

### Preconditions

* Python 2.6 and Graphviz 2.8+ along with its python bindings, available from graphviz.org as graphviz-<version>.rpm and
  graphviz-python-<version>.rpm. Source installs need to be built with --enable-python.
* MoinMoin 1.8+ installed.
* A MoinMoin wiki installed in directory WIKIDIR (with config directory in WIKIDIR/config and data in WIKIDIR/data)

### Steps

1. Install the python extension
   ```
   % python setup.py install
   ```

2. Install Hooks to be used with GraphingWiki
   ```
   % cat wikiconfig-add.txt >> /WIKIDIR/config/wikiconfig.py
   ```

3. Install plugins to wiki
   Add following (or your equivalent for the Python installation) to wikiconfig
   ```
   plugin_dirs = ['/usr/lib/python2.6/site-packages/graphingwiki/plugin']
   ```

4. Populate the graph data of existing pages
   ```
   % gwiki-rehash WIKIDIR
   ```

5. Optionally install usability add-ons (see
   [htdocs/gwikicommon/README](./htdocs/gwikicommon/README))

After this, you should be all set and ShowGraph should show in the
wiki's action menu. If not, check permissions of
site-packages/graphingwiki, site-packages/MoinMoin, plugins and
config.

## Scripts

For housekeeping and debugging.

**gwiki-get-tgz**

* Gets a graphingwiki revision from repository

**gwiki-rehash**

* Saves graph data from all the pages of a wiki.

**gwiki-showpage**

* A general CLI interface to a MoinMoin wiki

**gwiki-showgraph**

* Debug: A CLI interface to the showgraph-action.

**mm2gwiki**

* Import a freemind mind map to wiki pages
