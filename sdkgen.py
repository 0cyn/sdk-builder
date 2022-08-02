import subprocess
import multiprocessing
import concurrent.futures
import sys
import os
import glob
import ktool
import time


def system(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, echo=False):
    proc = subprocess.Popen("" + cmd,
                            shell=True)
    proc.communicate()
    return proc.returncode == 0


def system_with_output(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, echo=False):
    proc = subprocess.Popen("" + cmd,
                            stdout=stdout,
                            stderr=stderr,
                            shell=True)
    std_out, std_err = proc.communicate()
    return proc.returncode, std_out, std_err


def system_pipe_output(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, echo=False):
    if echo:
        print(cmd)

    process = subprocess.Popen(cmd,
                               stdout=stdout,
                               stderr=stderr,
                               shell=True)

    while True:
        realtime_output = process.stdout.readline()
        realtime_err = process.stderr.readline()

        if realtime_output == '' and realtime_err == '' and process.poll() is not None:
            break

        if realtime_output:
            print(realtime_output.strip(), flush=True)
        if realtime_err:
            print(realtime_err.strip(), flush=True, file=sys.stderr)


class IPSWAdapter:
    def __init__(self):
        self.ipsw_path = 'ipsw'

    def try_dl_and_extract(self, version, device, output_folder, max_dl_attempts=5):
        attempts = max_dl_attempts
        while attempts >= 0:
            if self.download(version, device):
                break
            attempts -= 1
            time.sleep(10)

        self.extract(output_folder)

    def extract(self, output_folder, ipsw_name='$(ls *.ipsw | xargs)'):
        if not system(f'{self.ipsw_path} extract -d {ipsw_name}'):
            return False
        if not system(f'mkdir -p {output_folder}'):
            return False
        if not system(f'mv $(find . -name dyld_shared_cache* | xargs) {output_folder}'):
            return False

    def download(self, version, device):
        if not system(f'{self.ipsw_path} download ipsw --version {version} --device {device}', echo=True):
            return False
        return True


class DEAdapter:
    def __init__(self):
        pass

    def extract_all(self, dsc_folder, output_folder):
        cwd = os.getcwd()
        os.chdir(dsc_folder)
        system(f'dyldex_all -j 1 dyld_shared_cache_arm64')
        system(f'mv binaries/System ./')
        os.chdir(cwd)
        system(f'mv {dsc_folder}/System/* {output_folder}')


def dump(filename):
    fd = open(f'{filename}', 'rb')

    library = ktool.load_image(fd, force_misaligned_vm=True)
    objc_lib = ktool.load_objc_metadata(library)

    tbd_text = ktool.generate_text_based_stub(library, compatibility=True)
    with open(f'{filename}.tbd', 'w') as tbd_out:
        tbd_out.write(tbd_text)

    os.makedirs(f'{os.path.dirname(filename)}/Headers', exist_ok=True)

    header_dict = ktool.generate_headers(objc_lib, sort_items=True)
    for header_name in header_dict:
        with open(f'{os.path.dirname(filename)}/Headers' + '/' + header_name,
                  'w') as out:
            out.write(str(header_dict[header_name]))


def trydump(item):
    try:
        print(f'Dumping {item}')
        dump(item)
    except Exception as ex:
        print(ex)
        print(f'{item} Fail')


if __name__ == "__main__":
    ipsw = IPSWAdapter()
    de = DEAdapter()

    vers = sys.argv[1]

    if not os.path.exists(f'{vers}.dsc'):
        ipsw.try_dl_and_extract(f'{vers}', 'iPhone10,3', f'{vers}.dsc')
    if not os.path.exists(f'{vers}.bins'):
        de.extract_all(f'{vers}.dsc', f'{vers}.bins')

    system(f"cp -r {vers}.bins {vers}.extracted")

    file_batch_list = []

    for filename in glob.iglob(f'{vers}.extracted/' + '**/**', recursive=True):
        if os.path.isfile(filename):
            file_batch_list.append(filename)

    public_frameworks = sorted(list(set(file_batch_list)))
    executor = concurrent.futures.ProcessPoolExecutor(multiprocessing.cpu_count()-1)
    futures = [executor.submit(trydump, (item)) for item in public_frameworks]
    concurrent.futures.wait(futures)
