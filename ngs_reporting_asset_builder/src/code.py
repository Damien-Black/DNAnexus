from __future__ import print_function
import os
import subprocess
import tempfile
import pipes
import dxpy
import glob
from platform import python_version


class args_fake():
    def __init__(self, name, title, description, version):
        self.name = name
        self.title = title
        self.description = description
        self.version = version


def run_cmd_arr(arr_cmd, output=False):
    print(" ".join([pipes.quote(a) for a in arr_cmd]))
    call = subprocess.check_output if output else subprocess.check_call
    out = call(arr_cmd)
    return out if output else None


def get_file_list(output_file, resources_to_ignore):
    """
    This method find all the files in the system and writes it to the output file
    """
    tmp_dir = os.path.dirname(output_file) + "*"
    cmd = ["sudo", "find", "/", "-or", "-path", "'/miniconda*'"]
    print("code.py: find cmd: " + " ".join(cmd))

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


def replace_in_file(fpath, url_mapping):
    with open(fpath, 'r') as file:
        filedata = unicode(file.read(), 'utf-8')
    for old, new in url_mapping.items():
        print('  replace ' + old + ' -> ' + new)
        filedata = filedata.replace(old, new)
    with open(fpath, 'w') as file:
        file.write(filedata.encode('utf-8'))


def output_test_files(final_dir):
    """Output files"""
    report_file_links = []
    # HTML reports
    multiqc_report = glob.glob(os.path.join(final_dir, "20??-??-??_*", "report.html"))
    if not multiqc_report:
        raise dxpy.exceptions.AppInternalError('Error: report.html not found for project ' + final_dir)
    multiqc_report = multiqc_report[0]
    print('MultiQC Test report: ' + multiqc_report)

    files_linked_to_multiqc = (
        glob.glob(os.path.join(final_dir, "20??-??-??_*", "call_vis.html")) +  # remove this line after update
        glob.glob(os.path.join(final_dir, "20??-??-??_*", "call_vis.part1.html")) +  # remove this line after update
        glob.glob(os.path.join(final_dir, "20??-??-??_*", "reports", "*.html")) +
        glob.glob(os.path.join(final_dir, "20??-??-??_*", "var", "vardict.PASS.txt")) +
        glob.glob(os.path.join(final_dir, "20??-??-??_*", "var", "vardict.paired.PASS.txt")) +
        glob.glob(os.path.join(final_dir, "20??-??-??_*", "var", "vardict.single.PASS.txt")) +
        glob.glob(os.path.join(final_dir, "20??-??-??_*", "cnv", "seq2c.tsv")) +
        glob.glob(os.path.join(final_dir, "20??-??-??_*", "log", "programs.txt")) +
        glob.glob(os.path.join(final_dir, "20??-??-??_*", "log", "data_versions.csv")))

    url_mapping = dict()
    print('Other Test reports:')
    for path in files_linked_to_multiqc:
        print('  ' + path)
        dxlink = dxpy.dxlink(dxpy.upload_local_file(filename=path, folder=os.path.dirname(path), parents=True))
        report_file_links.append(dxlink)
        dxurl = 'https://platform.dnanexus.com/' + os.environ['DX_PROJECT_CONTEXT_ID'] + '/' + dxlink['$dnanexus_link'] + '/view'
        relpath = os.path.relpath(path, os.path.dirname(multiqc_report))
        url_mapping[relpath] = dxurl

    print('Fixing links to reports in the MultiQC report')
    replace_in_file(multiqc_report, url_mapping)
    dxlink = dxpy.dxlink(dxpy.upload_local_file(filename=multiqc_report, folder=os.path.dirname(multiqc_report), parents=True))
    report_file_links.append(dxlink)

    # Other output files
    print('Other files:')
    for path in (
            glob.glob(os.path.join(final_dir, "20??-??-??_*", "var", "*.txt")) +
            glob.glob(os.path.join(final_dir, "20??-??-??_*", "var", "*.vcf.gz*")) +
            glob.glob(os.path.join(final_dir, "20??-??-??_*", "cnv", "*")) +
            glob.glob(os.path.join(final_dir, "*", "varFilter", "*")) +
            glob.glob(os.path.join(final_dir, "*", "*.anno.filt.vcf.gz*"))):
        relpath = os.path.relpath(path, os.path.dirname(multiqc_report))
        if relpath not in url_mapping:  # file not yet uploaded
            print('  ' + path)
            dxlink = dxpy.dxlink(dxpy.upload_local_file(filename=path, folder=os.path.dirname(path), parents=True))
            report_file_links.append(dxlink)

    return report_file_links


@dxpy.entry_point("main")
def main(**kwargs):
    print("Start")
    before_file_list_path = os.path.join(tempfile.gettempdir(), "before-sorted.txt")
    print("before_file_list_path: " + before_file_list_path)
    get_system_snapshot(before_file_list_path, [])

    print('Making Asset')
    os.chdir("/")
    run_cmd_arr(['wget', 'https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh', '-O', 'miniconda.sh'])
    run_cmd_arr(['bash', 'miniconda.sh', '-b', '-p', '/miniconda'])
    conda_cmd = os.path.join('/', 'miniconda', 'bin', 'conda')
    run_cmd_arr([conda_cmd, 'config', '--set', 'always_yes', 'yes', '--set', 'changeps1', 'no'])
    run_cmd_arr([conda_cmd, 'update', '-q', 'conda'])

    # conda create ngs_reporting
    py_ver = os.path.splitext(python_version())[0]
    print("Python Version:", py_ver)
    run_cmd_arr([conda_cmd, 'create', '-y', '-q', '-n', 'ngs_reporting', '-c', 'vladsaveliev', '-c', 'bioconda', '-c', 'r', '-c',
                 'conda-forge', 'python={py_ver}'.format(py_ver=py_ver), 'ngs_reporting'])

    # Run Test
    os.chdir(os.path.expanduser('~'))
    print("Preparing Test Suite")
    run_cmd_arr(['git', 'clone', 'https://github.com/vladsaveliev/NGS_Reporting_TestData'])
    os.environ['PATH'] += os.pathsep + '/miniconda/envs/ngs_reporting/bin' + os.pathsep + '/miniconda/bin'
    os.environ['CONDA_DEFAULT_ENV'] = 'ngs_reporting'

    dream_dir = os.path.join('/', 'dream_chr21')
    final_dir = os.path.join(dream_dir, 'final')
    sys_yaml = '/reference_data/system_info_DNAnexus.yaml'
    postproc_cmdl = ['bcbio_postproc', '--sys-cfg', sys_yaml, final_dir]
    run_cmd_arr(postproc_cmdl)
    print('Uploading Test reports for manual Verification')
    test_results = output_test_files(final_dir)

    print("Creating Asset")
    # Create asset
    asset_name = "ngs_reporting_asset"
    asset_title = "NGS reporting Asset"
    description = "AZ post-processing suite for https://github.com/chapmanb/bcbio-nextgen: mutation and coverage prioritisation, visualisation, reporting and exposing.\nConda command: {conda_cmd}\nActivate ngs_reporting environment: /miniconda/bin/conda activate ngs_reporting".format(conda_cmd=conda_cmd)
    asset_version = "0.0.2"  # Get proper version info, probably from conda
    create_output = run_cmd_arr(
        ["create-asset", "--name", asset_name, "--title", asset_title, "--description", description, "--version", asset_version],
        output=True)

    # Output test results
    print('Asset created, be sure to manually review test results')
    record_id = create_output.split('\n')[-2]
    job_proj = dxpy.DXContainer(dxpy.WORKSPACE_ID)
    job_proj.new_folder(folder="/asset_creation_test_results")
    job_proj.move_folder(folder="/dream_chr21", destination="/asset_creation_test_results")

    return {
        'test_report_files': test_results,
        'asset_object': dxpy.dxlink(record_id)}
