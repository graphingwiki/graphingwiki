# -*- coding: utf-8 -*-
from distutils.core import setup

setup(name='opencollab', version='457',
      author='Joachim Viide, Pekka Pietikäinen, Mika Seppänen',
      author_email='contact@clarifiednetworks.com',
      description='OpenCollab XML-RPC SDK',
      packages=['opencollab'],
      package_data={'opencollab': ['*.py']},
      scripts=[ 'scripts/opencollab-agent',
        'scripts/opencollab-clone-pages',
        'scripts/opencollab-create-gallery',
        'scripts/opencollab-delete-pages',
        'scripts/opencollab-downloader',
        'scripts/opencollab-import-mresolved',
        'scripts/opencollab-push-tickets',
        'scripts/opencollab-uploader'])

