from setuptools import setup, find_packages

setup(
    name='load_codes',
    author='arb',
    author_email='arb.trops@gmail.com',
    description='load_codes de ouf',
    version='1.7.1',
    packages=find_packages(),
    install_requires=['arb_logger', 'arb_defines', 'db_handler'],
    entry_points={
        'console_scripts': [
            'load_codes = load_codes.loader:main',
        ]
    },
)
