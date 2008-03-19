# -*- coding: utf-8 -*-
from distutils.core import setup

setup(name='opencollab', version='360',
      author='Joachim Viide, Pekka Pietikäinen, Mika Seppänen',
      author_email='contact@clarifiednetworks.com',
      description='OpenCollab XML-RPC SDK',
      packages=['opencollab'],
      package_dir={'': 'opencollab'},
      package_data={'opencollab': ['opencollab/*.py']},
      scripts=['scripts/opencollab-uploader', 
        'scripts/opencollab-downloader',
        'scripts/opencollab-push-tickets'])

