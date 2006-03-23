from distutils.core import setup

setup(name='graphingwiki', version='0.1',
      author='Juhani Eronen, Joachim Viide',
      author_email='exec@ee.oulu.fi',
      description='Graph handling for the Graphingwiki MoinMoin extension',
      py_modules=['graphingwiki/graph', 'graphingwiki/graphrepr',
                  'graphingwiki/patterns', 'graphingwiki/sync'])
