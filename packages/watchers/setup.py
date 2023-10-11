from setuptools import setup, find_packages

setup(
    name='watchers',
    author='arb',
    author_email='arb.trops@gmail.com',
    description='watchers de ouf',
    version='1.4.0',
    packages=find_packages(),
    install_requires=[
        'arb_logger', 'arb_defines', 'db_handler', 'redis_manager',
        'exchange_api', 'feed_handler', 'standalone_tools'
    ],
    entry_points={
        'console_scripts': [
            # SCRIPTS
            'cancel_order = watchers.cancel_order:main',
            'single_order = watchers.single_order:main',
            # WATCHERS
            'tick_watcher = watchers.watchers.tick_watcher:main',
            'spread_watcher = watchers.watchers.spread_watcher:main',
            'multi_exch_spread_watcher = watchers.watchers.multi_exch_spread_watcher:main',
            # SENTINELS
            'atr_sentinel = watchers.sentinels.atr_sentinel:main',
            'candle_sentinel = watchers.sentinels.candle_sentinel:main',
            'target_sentinel = watchers.sentinels.target_sentinel:main',
            'pair_zscore_sentinel = watchers.sentinels.pair_zscore_sentinel:main',
            'i_ob_imb_sentinel = watchers.sentinels.i_ob_imb_sentinel:main',
            'price_impact_sentinel = watchers.sentinels.price_impact_sentinel:main',
            # TRIGGERS
            'roller = watchers.triggers.roller:main',
            'mm_dumb = watchers.triggers.mm_dumb:main',
            'mm_grid = watchers.triggers.mm_grid:main',
            'mm_trigger = watchers.triggers.mm_trigger:main',
            'spread_trigger = watchers.triggers.spread_trigger:main',
            'spread_trigger_liq = watchers.triggers.spread_trigger_liq:main',
            'spread_trigger_liq_wait = watchers.triggers.spread_trigger_liq_wait:main',
            # SEEKERS
            'pair_seeker = watchers.seekers.pair_seeker:main',
            'target_seeker = watchers.seekers.target_seeker:main',
            'sample_seeker = watchers.seekers.sample_seeker:main',
        ]
    },
)
