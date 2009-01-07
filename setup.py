from distutils.core import setup
setup(name='raippa',
    packages=['raippa'],
    package_dir={'raippa': 'src'},
    package_data={'raippa': ['plugin/*/*.py']},
    scripts=['scripts/raippa-install']
    )
