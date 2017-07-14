from __future__ import print_function
import os
import subprocess
import tempfile
import time
import pipes
import dxpy
import shutil
from platform import python_version


class args_fake():
    def __init__(self, name, title, description, version):
        self.name = name
        self.title = title
        self.description = description
        self.version = version


def run_cmd_arr(arr_cmd):
    print(" ".join([pipes.quote(a) for a in arr_cmd]))
    subprocess.check_call(arr_cmd)


def get_file_list(output_file, resources_to_ignore):
    """
    This method find all the files in the system and writes it to the output file
    """
    tmp_dir = os.path.dirname(output_file) + "*"
    skipped_paths = ["/proc*", tmp_dir, "/run*", "/boot*", "/home/dnanexus*", "/sys*",
                     "/dev*"]
    cmd = ["sudo", "find", "/"]
    for ignore_dir in skipped_paths + resources_to_ignore:
        cmd.extend(["-not", "-path", ignore_dir])

    env = os.environ.copy()
    env['LC_ALL'] = 'C'
    ps_pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    ps_file = subprocess.Popen(["sort"], stdin=ps_pipe.stdout, stdout=subprocess.PIPE, env=env)

    with open(output_file, "w") as bfile:
        for line in ps_file.stdout:
            sp_code = ps_file.poll()
            file_name = line.rstrip()
            if file_name == "":
                if sp_code is not None:
                    break
                else:
                    continue
            if file_name == "/":
                continue
            try:
                mtime = str(os.path.getmtime(file_name))
            except OSError as os_err:
                print(os_err)
                mtime = ''
            # file_name should not have special characters
            bfile.write(file_name + "\t" + str(mtime) + '\n')
    ps_file.stdout.close()


def get_system_snapshot(output_file_path, ignore_files):
    tmp_file_path = tempfile.mktemp()
    get_file_list(tmp_file_path, ignore_files)
    with open(output_file_path, 'w') as output_file_handle:
        proc = subprocess.Popen(['sort', tmp_file_path], stdout=output_file_handle)
        proc.communicate()


@dxpy.entry_point("main")
def main(**kwargs):
    print("Start")
    before_file_list_path = os.path.join(tempfile.gettempdir(), "before-sorted.txt")
    get_system_snapshot(before_file_list_path, [])
    print('Making Asset')
    # Do stuff on worker to create ngs_reporting asset by Vlad
    # Sleep instance for ssh-in purposes, add tag "done" when finished
    # job_dx = dxpy.DXJob(os.environ["DX_JOB_ID"])
    # descr = job_dx.describe()
    # while "done" not in descr["tags"]:
    #     time.sleep(60)
    #     descr = job_dx.describe()
    # print("Creating asset")

    os.chdir("/")

    run_cmd_arr(['wget', 'https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh', '-O', 'miniconda.sh'])
    run_cmd_arr(['bash', 'miniconda.sh', '-b', '-p', '/miniconda'])
    conda_cmd = os.path.join('/', 'miniconda', 'bin', 'conda')
    run_cmd_arr([conda_cmd, 'config', '--set', 'always_yes', 'yes', '--set', 'changeps1', 'no'])
    run_cmd_arr([conda_cmd, 'update', '-q', 'conda'])
    print("Copy resources/reference_data to /miniconda/reference_data")
    shutil.copytree("reference_data", "miniconda/reference_data")
    # conda create ngs_reporting
    py_ver = os.path.splitext(python_version())[0]
    print("Python Version:", py_ver)
    run_cmd_arr([conda_cmd, 'create', '-y', '-q', '-n', 'ngs_reporting', '-c', 'vladsaveliev', '-c', 'bioconda', '-c', 'r', '-c',
                 'conda-forge', 'python={py_ver}'.format(py_ver=py_ver), 'ngs_reporting'])
    repo_dir = os.path.abspath('NGS_Reporting')
    run_cmd_arr(["git", "clone", "https://github.com/AstraZeneca-NGS/NGS_Reporting", repo_dir])
    os.chdir(repo_dir)
    run_cmd_arr(["python", "setup.py", "install", "--single-version-externally-managed", "--record=record.txt"])
    os.chdir("/")

    # Create asset
    asset_name = "ngs_reporting_asset"
    asset_title = "NGS reporting Asset"
    description = "AZ post-processing suite for https://github.com/chapmanb/bcbio-nextgen: mutation and coverage prioritisation, visualisation, reporting and exposing.\nConda command: {conda_cmd}\nActivate ngs_reporting environment: /miniconda/bin/conda activate ngs_reporting".format(conda_cmd=conda_cmd)
    asset_version = "0.0.2"  # Get proper version info, probably from conda
    run_cmd_arr(["create-asset", "--name", asset_name, "--title", asset_title, "--description", description, "--version", asset_version]) 
