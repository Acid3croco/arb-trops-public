from setuptools import setup, find_packages

setup(
    name='arb_utils',
    author='arb',
    author_email='arb.trops@gmail.com',
    description='arb_utils de ouf',
    version='1.0.0',
    packages=find_packages(),
    install_requires=['arb_defines', 'db_handler'],
)
