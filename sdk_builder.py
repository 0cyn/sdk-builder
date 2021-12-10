"""

"""

import os
import time
import concurrent.futures
import ktool
import shutil

start_ts = time.time()

classmap = {}

working_dir = ".sdkbuilder"


def dump(fold, fw_name):
    fd = open(f'./System/Library/{fold}/{fw_name}.framework/{fw_name}', 'rb')
    
    library = ktool.load_image(fd)
    objc_lib = ktool.load_objc_metadata(library)
        
    os.makedirs(f'{working_dir}/System/Library/{fold}/{fw_name}.framework', exist_ok=True)
    shutil.copyfile(f'./System/Library/{fold}/{fw_name}.framework/{fw_name}', f'{working_dir}/System/Library/{fold}/{fw_name}.framework/{fw_name}')
    
    tbd_text = ktool.generate_text_based_stub(library, compatibility=True)
    with open(f'{working_dir}/System/Library/{fold}/{fw_name}.framework/{fw_name}.tbd', 'w') as tbd_out:
        tbd_out.write(tbd_text)
        
    os.makedirs(f'{working_dir}/System/Library/{fold}/{fw_name}.framework/Headers', exist_ok=True)
    
    header_dict = ktool.generate_headers(objc_lib, sort_items=True)
    for header_name in header_dict:
        with open(f'{working_dir}/System/Library/{fold}/{fw_name}.framework/Headers' + '/' + header_name,
                  'w') as out:
            out.write(header_dict[header_name])


def trydump(item):
    fold, fw_name = item
    try:
        print(f'Dumping {fold} ' + fw_name)
        dump(fold, fw_name.split('.')[0])
    except Exception as ex:
        print(ex)
        print(f'{fw_name} Fail')

if __name__ == '__main__':

    public_frameworks = []

    for fw in os.listdir('./System/Library/Frameworks/'):
        public_frameworks.append(fw)
    
    public_frameworks = sorted(public_frameworks)
    executor = concurrent.futures.ProcessPoolExecutor(3)
    futures = [executor.submit(trydump, ('Frameworks', item)) for item in public_frameworks]
    concurrent.futures.wait(futures)

    privateframeworks = []

    for fw in os.listdir('./System/Library/PrivateFrameworks/'):
        privateframeworks.append(fw)

    privateframeworks = sorted(privateframeworks)

    executor = concurrent.futures.ProcessPoolExecutor(3)
    futures = [executor.submit(trydump, ('PrivateFrameworks', item)) for item in privateframeworks]
    concurrent.futures.wait(futures)
