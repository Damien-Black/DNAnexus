#!/usr/bin/env python
# ngs_reporting_oncology 0.0.1
# Generated by dx-app-wizard.
#
# Basic execution pattern: Your app will run on a single machine from
# beginning to end.
#
# See https://wiki.dnanexus.com/Developer-Portal for documentation and
# tutorials on how to modify this file.
#
# DNAnexus Python Bindings (dxpy) documentation:
#   http://autodoc.dnanexus.com/bindings/python/current/

from __future__ import print_function
import os
import dxpy
import subprocess
import re
import time
import glob

PATTERN_MAPPING = {
    re.compile('^file-[0-9A-Za-z]{24}$'): dxpy.DXFile
}


def download_job_inputs(input_dict):
    """Download files objects and update job input dict
    Updates all values that contain a dxlink
    """
    def create_dx_data_obj(inp_val):
        # TODO support getting outgoing file-id from DXRecords
        if type(inp_val) is not dict or '$dnanexus_link' not in inp_val:
            return
        dx_id = inp_val['$dnanexus_link']
        for reg_obj, dxmatch in PATTERN_MAPPING.iteritems():
            if reg_obj.match(dx_id):
                return dxmatch(dx_id)
    for inp_name, val in input_dict.iteritems():
        f_dx = create_dx_data_obj(val)
        print("f_dx: " + str(f_dx))
        if f_dx is not None:
            f_path = f_dx.name
            dxpy.download_dxfile(f_dx, f_path)
            input_dict[inp_name] = {
                "dxFileObj": f_dx,
                "filePath": f_path
            }
    return input_dict


def get_opts(updated_input_dict):
    """Add optional parameters"""
    OPT_CMD = {
        # 'sys_info_yaml': '--sys-cfg {param}',
    }
    cmd_opt = []
    for inp, val in updated_input_dict.iteritems():
        opt_str = OPT_CMD.get(inp)
        if opt_str is None:
            continue
        param = val.get('filePath') if type(val) is dict else val
        cmd_opt.append(opt_str.format(param=param))
    return cmd_opt


def run_cmdl(cmdl):
    print(" ".join(cmdl))
    subprocess.check_call(cmdl)


@dxpy.entry_point('main')
def main(**job_inputs):
    # Biolerplate for debugging and ngs_report scripts
    # data_dir = os.path.join(os.path.expanduser('~'), 'Data')
    # os.mkdir(data_dir)
    # Download inputs
    print('PATH = ' + str(os.environ['PATH']))
    os.environ['PATH'] += os.pathsep + '/miniconda/envs/ngs_reporting/bin' + os.pathsep + '/miniconda/bin'
    os.environ['CONDA_DEFAULT_ENV'] = 'ngs_reporting'
    print('PATH = ' + str(os.environ['PATH']))
    run_cmdl(['which', 'bcbio_postproc'])
    run_cmdl(['bcbio_postproc', '--version'])

    # print()
    # print('Removing NGS_Reporting from conda envirnoment to reinstall it from source')
    # run_cmdl(["conda", "remove", "ngs_reporting", "-y"])
    # print('Cloning the repository to get the latest source code')
    # run_cmdl(["git", "clone", "https://github.com/AstraZeneca-NGS/NGS_Reporting"])
    # os.chdir("NGS_Reporting")
    # run_cmdl(["pip", "install", "--upgrade", "pip"])
    # run_cmdl(["pip", "install", "--upgrade", "--ignore-installed", "setuptools"])
    # run_cmdl(["python", "setup.py", "install"])
    # os.chdir("..")
    # run_cmdl(['which', 'bcbio_postproc'])
    # run_cmdl(['bcbio_postproc', '--version'])

    print()
    sys_yaml = '/reference_data/system_info_Nexus_Test.yaml'
    if os.path.isfile(sys_yaml):
        print('Sys yaml ' + sys_yaml + ' exists')
    else:
        print('Sys yaml ' + sys_yaml + ' does not exist')

    postproc_cmdl = ['bcbio_postproc', '-d', '--sys-cfg', sys_yaml]

    print("job_inputs: " + str(job_inputs))
    job_inputs = download_job_inputs(job_inputs)
    print("updated job_inputs: " + str(job_inputs))
    postproc_cmdl.extend(get_opts(job_inputs))

    bcbio_dir = job_inputs['bcbio_dir']
    if not bcbio_dir.startswith('/'):
        bcbio_dir = '/' + bcbio_dir
    print('Calling download_platform_folder_with_exclusion')
    copy_folder_to_proj(src_proj=os.environ['DX_PROJECT_CONTEXT_ID'], src_proj_fld=bcbio_dir, target_fld_prefix='')

    # bcbio_tar = job_inputs['bcbio_tar']['filePath']
    # print('Bcbio tar:', bcbio_tar)
    # cmdl = ['tar', '-xvf', bcbio_tar]
    # print('Extracting: ' + ' '.join(cmdl))
    # subprocess.check_call(cmdl)
    # bcbio_dir = bcbio_tar.replace('.tar.gz', '').replace('.tar', '')
    print('Bcbio directory:', bcbio_dir)
    postproc_cmdl.append(bcbio_dir)

    print('Runing post-processing with the command: "' + " ".join(postproc_cmdl) + '"')
    subprocess.check_call(postproc_cmdl)

    # Output files
    report_file_links = []
    print('Output files to expose:')
    for item_path in (
        glob.glob(os.path.join(bcbio_dir, "final*", "20??-??-??_*", "report.html")) + 
        glob.glob(os.path.join(bcbio_dir, "final*", "20??-??-??_*", "reports", "*.html")) + 
        glob.glob(os.path.join(bcbio_dir, "final*", "20??-??-??_*", "var", "*.txt"))):
        print(item_path)
        if os.path.isfile(item_path):
            report_file_links.append(
                dxpy.dxlink(dxpy.upload_local_file(
                    filename=item_path,
                    folder=bcbio_dir,  # you can reuse bcbio_output_dir_on_local here to mimic structure
                    parents=True))) # again parent just makes fodlers if they arent there

    output = {'report_files': report_file_links}

    # report_paths = glob.glob(os.path.join(bcbio_dir, "final*", "20??-??-??_*", "report.html"))
    # if not report_paths:
    #     print('Error: report.html not found for project ' + bcbio_dir)
    # else:
    #     report_path = report_paths[0]
    #     output['html_report'] = dxpy.dxlink(dxpy.upload_local_file(report_path))

    return output


def copy_folder_to_proj(src_proj, target_proj=None, src_proj_fld=None, target_fld_prefix=None, exclude_func=None):
    """Copies folder from src_proj to target_proj under target_proj_fld_prefix
    Args:
            target_proj: Destination project. If not specified local machine is assumed.
            src_proj_fld: Source folder to copy from. If None, project root is assumed.
            target_fld_prefix: Prefix to prepend to copied folders. Defaults to Root if not specified
            exclude_func: func that is passed the describe results of a dxobject and returns a boolean.
                True - file is copied, False - Not copied over.
    """
    def transfer_to_project(file_id, file_dxpath, file_name):
        f_dx = dxpy.DXFile(file_id, project=src_proj)
        prefix = "/" if target_fld_prefix is None else target_fld_prefix
        file_dxpath = os.path.join(prefix, file_dxpath)
        file_platform_url = f_dx.get_download_url(duration=3600, preauthenticated=True)[0]
        url_fetcher_input = {'url': file_platform_url, 'output_name': file_name}
        url_fetcher_appdx.run(
            app_input=url_fetcher_input, project=target_proj,
            folder=file_dxpath)

    def download_to_local(file_id, file_dxpath, file_name):
        # Just creating a directory for saftey
        prefix = "Downloaded_Files_dir_{}".format(time.time()) if target_fld_prefix is None else target_fld_prefix
        file_dir = os.path.join(prefix, file_dxpath)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        file_download_path = os.path.join(file_dir, file_name)
        if os.path.isfile(file_download_path):
            print('Found {fn} at {fpath}'.format(
                fn=file_name, fpath=file_download_path))
            return
        print('downloading {fn} to {fdir}'.format(
            fn=file_name, fdir=file_dir))
        dxpy.download_dxfile(file_id, file_download_path)

    url_fetcher_appdx = dxpy.DXApp('app-F4qJ1189b249vy69G1vF5jqf')
    fetch_func = download_to_local if target_proj is None else transfer_to_project

    file_describes = dxpy.find_data_objects(
        classname='file', state='closed', visibility='visible',
        project=src_proj, folder=src_proj_fld, describe=True)

    for file_describe in file_describes:
        if exclude_func is not None and exclude_func(file_describe):
            continue
        fetch_func(
            file_id=file_describe['id'],
            file_dxpath=file_describe['describe']['folder'],
            file_name=file_describe['describe']['name'])



dxpy.run()
