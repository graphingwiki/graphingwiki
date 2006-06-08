from distutils.core import setup

setup(name='graphingwiki', version='0.1',
      author='Juhani Eronen, Joachim Viide, Aki Helin',
      author_email='exec@iki.fi',
      description='Graph handling for the Graphingwiki MoinMoin extension',
      packages=['graphingwiki'],
      package_dir={'graphingwiki': 'graphingwiki'},
      package_data={'graphingwiki': ['plugin/*/*.py']},
      scripts=['scripts/gwiki-rehash', 'scripts/gwiki-showgraph',
               'scripts/gwiki-debuggraph', 'scripts/gwiki-install'])
