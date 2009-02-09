# -*- coding: utf-8 -*-
from distutils.core import setup

setup(name='opencollab', version='627',
      author='Joachim Viide, Pekka Pietikäinen, Mika Seppänen',
      author_email='contact@clarifiednetworks.com',
      description='OpenCollab XML-RPC SDK',
      packages=['opencollab'],
      package_data={'opencollab': ['*/*.py']},
      scripts=[ 'scripts/opencollab-agent',
        'scripts/opencollab-codetools-uploader',
        'scripts/opencollab-clone-pages',
        'scripts/opencollab-create-gallery',
        'scripts/opencollab-defensics-uploader',
        'scripts/opencollab-delete-pages',
        'scripts/opencollab-downloader',
        'scripts/opencollab-import-mresolved',
        'scripts/opencollab-import-nvd-xml',
        'scripts/opencollab-multi-resolver',
        'scripts/opencollab-notifier',
        'scripts/opencollab-nmap-uploader',
        'scripts/opencollab-push-tickets',
        'scripts/opencollab-remove-dups',
        'scripts/opencollab-spam-reader',
        'scripts/opencollab-upload-identities',
        'scripts/opencollab-uploader'])

