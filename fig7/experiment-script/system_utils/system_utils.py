import glob
from subprocess import Popen, PIPE, run
import os
import shutil


def execute_cmd(cmd):
    """
    Execute the external command and get its exitcode, stdout and stderr.
    """
    #args = shlex.split(cmd)

    #print("executing {}".format(cmd))
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    proc.wait()

    out, err = proc.communicate()
    exitcode = proc.returncode
    #print("done executing, stdout: {}, err: {}".format(out, err))
    #
    return exitcode, out, err


def execute_cmd_silently(cmd):
    proc = Popen(cmd, shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)


def execute_cmd_detach_log(cmd, filename):
    with open(filename, "w") as log:
        proc = Popen(cmd, shell=True, stdin=None, stdout=log, stderr=log, close_fds=True)

def execute_cmd_log(cmd, filename):
    with open(filename, "w") as log:
        proc = Popen(cmd, shell=True, stdin=None, stdout=log, stderr=log, close_fds=True)
        proc.wait()


def clear_os_cache():
    execute_cmd("sync ; echo 1 | sudo tee /proc/sys/vm/drop_caches") # Note, needs sudo priviledges for that...


def flush_os_cache():
    execute_cmd("sync")


def start_disk_monitor(file):
    execute_cmd_detach_log("iostat -sdymtz -o JSON 1", file)


def stop_disk_monitor():
    execute_cmd("pkill -f iostat -2")


def empty_dir(directory):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


def empty_cache_dir(directory):
    execute_cmd("cd " + directory + " ; rm ./*.easl ; rm ./*.metadata")


def make_dir(directory):
    os.makedirs(directory, exist_ok=True)




