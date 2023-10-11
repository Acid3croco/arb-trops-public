import os
import sys
import shutil

from pathlib import Path

root_path = sys.argv[1]
root_path = Path(root_path)
all_dir = [
    x for x in root_path.iterdir() if x.is_dir() and x.stem != 'feed_handler'
]
print(all_dir)

lesetup = Path('feed_handler', 'setup.py')

for dir in all_dir:
    if not Path(dir / dir).exists():
        os.mkdir(dir / dir)
    for file in dir.iterdir():
        if file.stem != dir.stem:
            file.rename(dir / file)
    setup_file = Path(dir / 'setup.py')
    if not setup_file.exists():
        shutil.copy(lesetup, dir / 'setup.py')
        setup_file.write_text(setup_file.read_text().replace(
            'feed_handler', dir.stem))
