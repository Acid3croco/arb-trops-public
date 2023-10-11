import os

from pathlib import Path
from datetime import datetime

from tqdm import tqdm

from recorders.base_recorder import BaseRecorder

record_path = os.getenv('ARB_RECORDS_PATH')

all_files = Path(record_path).glob('*')


def create_folder(path):
    if path.parent.exists() is False:
        print('creating folder', path.parent)
        path.parent.mkdir(parents=True)


def move_file(file):
    recorder_type = file.stem.split('_')[0]

    if recorder_type == 'l2':
        recorder_type = 'l2_book'

    if recorder_type == 'candles':
        timeframe = file.stem.split('_')[1]
        target_path = Path(record_path) / 'candles' / timeframe / file.name
    else:
        instr_id = file.stem.split('_')[-2]
        date = file.stem.split('_')[-1]
        date = datetime.strptime(date, '%Y%m%d')
        target_path = BaseRecorder.get_record_path(recorder_type, instr_id,
                                                   date)
    print(file, target_path)
    create_folder(target_path)
    file.rename(target_path)


def main():
    for file in tqdm(all_files):
        print(file)
        try:
            move_file(file)
        except Exception as e:
            print(e)
            print(f'skipping file {file}')
            continue


if __name__ == '__main__':
    main()
