from distutils.core import setup

setup(name='opencollab', version='341',
      author='Joachim Viide',
      author_email='contact@clarifiednetworks.com',
      description='OpenCollab XML-RPC SDK',
      packages=['opencollab'],
      package_dir={'opencollab': 'lib'},
      package_data={'': ['lib/*.py']},
      scripts=['scripts/opencollab-uploader'])

