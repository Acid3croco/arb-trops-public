from setuptools import setup, find_packages

setup(
    name='redis_manager',
    author='arb',
    author_email='arb.trops@gmail.com',
    description='redis_manager de ouf',
    version='1.1.1',
    packages=find_packages(),
    install_requires=['arb_logger', 'arb_defines'],
)
