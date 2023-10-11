from setuptools import setup, find_packages

setup(
    name='exchange_api',
    author='arb',
    author_email='arb.trops@gmail.com',
    description='exchange_api de ouf',
    version='1.0.2',
    packages=find_packages(),
    install_requires=[
        'arb_logger', 'arb_defines', 'db_handler', 'redis_manager'
    ],
    entry_points={
        'console_scripts': [
            'exchange_api = exchange_api.exchange_api:main',
            'start_api = exchange_api.start_api:main',
            'stop_api = exchange_api.stop_api:main',
            'list_api = exchange_api.list_api:main',
        ]
    },
)
