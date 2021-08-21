"""

"""

import os
import time
import concurrent.futures
from ktool.macho import MachOFile
from ktool.objc import ObjCLibrary, LinkedClass
from ktool.dyld import Dyld
from ktool.generator import TBDGenerator
from ktool.headers import HeaderGenerator
from ktool.util import TapiYAMLWriter
import shutil

start_ts = time.time()

classmap = {}

working_dir = ".sdkbuilder"


def dump(fold, fw_name):
    fd = open(f'./System/Library/{fold}/{fw_name}.framework/{fw_name}', 'rb')
    machofile = MachOFile(fd)
    library = Dyld.load(machofile.slices[0])
    objc_lib = ObjCLibrary(library)

    hg = HeaderGenerator(objc_lib)
    os.makedirs(f'{working_dir}/System/Library/{fold}/{fw_name}.framework', exist_ok=True)
    shutil.copyfile(f'./System/Library/{fold}/{fw_name}.framework/{fw_name}', f'{working_dir}/System/Library/{fold}/{fw_name}.framework/{fw_name}')
    
    tbd_dict = TBDGenerator(library, True, objc_lib).dict
    with open(f'{working_dir}/System/Library/{fold}/{fw_name}.framework/{fw_name}.tbd', 'w') as tbd_out:
        tbd_out.write(TapiYAMLWriter.write_out(tbd_dict))
        
    os.makedirs(f'{working_dir}/System/Library/{fold}/{fw_name}.framework/Headers', exist_ok=True)
    for oclass in objc_lib.classlist:
        for header_name in hg.headers:
            with open(f'{working_dir}/System/Library/{fold}/{fw_name}.framework/Headers' + '/' + header_name,
                      'w') as out:
                out.write(str(hg.headers[header_name]))


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

    #for fw in os.listdir('./System/Library/Frameworks/'):
    #    public_frameworks.append(fw)

    #public_frameworks = sorted(public_frameworks)

    #executor = concurrent.futures.ProcessPoolExecutor(2)
    #futures = [executor.submit(trydump, ('Frameworks', item)) for item in public_frameworks]
    #concurrent.futures.wait(futures)

    privateframeworks = []

    for fw in os.listdir('./System/Library/PrivateFrameworks/'):
        privateframeworks.append(fw)

    privateframeworks = sorted(privateframeworks)

    executor = concurrent.futures.ProcessPoolExecutor(2)
    futures = [executor.submit(trydump, ('PrivateFrameworks', item)) for item in privateframeworks]
    concurrent.futures.wait(futures)
