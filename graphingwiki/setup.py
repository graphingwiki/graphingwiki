from distutils.core import setup

old_plugins = {'action': ['ShowProcessGraph.py', 'MetaCSV.py', 'metaCVS.py',
                          'ShowGraphIE.py', 'MetaTableEdit.py',
                          'ShowLatexSource.py', 'metaRadarDiagram.py',
                          'metaeditform.py'],
               'macro': ['metaRadarDiagram.py'],
               'script': ['scripts/gwiki-debuggraph', 'scripts/moin-showpage', 
                          'scripts/moin-editpage']}

setup(name='graphingwiki', version='0.1',
      author='Juhani Eronen, Joachim Viide, Aki Helin',
      author_email='exec@iki.fi',
      description='Graph handling for the Graphingwiki MoinMoin extension',
      packages=['graphingwiki'],
      package_dir={'graphingwiki': 'graphingwiki'},
      package_data={'graphingwiki': ['plugin/*/*.py', "plugin/__init__.py"]},
      scripts=['scripts/gwiki-rehash', 'scripts/gwiki-showgraph',
               'scripts/gwiki-install', 'scripts/gwiki-showpage', 
               'scripts/mm2gwiki.py', 'scripts/gwiki-editpage',
               'scripts/gwiki-xml-attachfile',
               'scripts/gwiki-get-tgz', 'scripts/gwiki-xml-meta'])

