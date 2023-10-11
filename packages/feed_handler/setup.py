from setuptools import setup, find_packages

setup(
    name='feed_handler',
    author='arb',
    author_email='arb.trops@gmail.com',
    description='feed_handler de ouf',
    version='2.4.0',
    packages=find_packages(),
    install_requires=[
        'arb_logger', 'arb_defines', 'db_handler', 'redis_manager'
    ],
    entry_points={
        'console_scripts': [
            'list_fh = feed_handler.list_fh:main',
            'start_fh = feed_handler.start_fh:main',
            'stop_fh = feed_handler.stop_fh:main',
            'feed_handler = feed_handler.feed_handler:main',
        ]
    },
)
