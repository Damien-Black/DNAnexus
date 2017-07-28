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
import glob
from yaml import load as load_yaml

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


def replace_in_file(fpath, url_mapping):
    with open(fpath, 'r') as file:
        filedata = unicode(file.read(), 'utf-8')
    for old, new in url_mapping.items():
        print('  replace ' + old + ' -> ' + new)
        filedata = filedata.replace(old, new)
    with open(fpath, 'w') as file:
        file.write(filedata.encode('utf-8'))


def copy_platform_folder_to_local(src_proj, src_proj_fld=None, dest_fld_prefix=None, exclude_func=None):
    """Copies folder from src_proj to target_proj under target_proj_fld_prefix

    Args:
            src_proj_fld: Source folder to copy from. If None, project root is assumed.
            dest_fld_prefix: Prefix to prepend to copied folders.
                               Defaults {project}/ on local
            exclude_func: func that is passed the describe results of a dxobject and returns a boolean.
                True - file is not copied, False - File is copied over.
    """
    def download_to_local(file_id, file_dxpath, file_name):
        file_dir = os.path.join(prefix, file_dxpath.strip('/'))
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

    proj_name = dxpy.DXProject(src_proj).name
    prefix = proj_name if dest_fld_prefix is None else dest_fld_prefix

    print('Searching {fld} in project {proj}'.format(
        fld=src_proj_fld if src_proj_fld else 'root', proj=proj_name))
    file_describes = dxpy.find_data_objects(
        classname='file', state='closed', visibility='visible',
        project=src_proj, folder=src_proj_fld, describe=True)

    for file_describe in file_describes:
        if exclude_func is not None and exclude_func(file_describe):
            continue
        download_to_local(
            file_id=file_describe['id'],
            file_dxpath=file_describe['describe']['folder'],
            file_name=file_describe['describe']['name'])


@dxpy.entry_point('main')
def main(**job_inputs):
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

    sys_yaml = '/reference_data/system_info_DNAnexus.yaml'
    if os.path.isfile(sys_yaml):
        print('Sys yaml ' + sys_yaml + ' exists')
    else:
        print('Sys yaml ' + sys_yaml + ' does not exist')

    postproc_cmdl = ['bcbio_postproc', '--sys-cfg', sys_yaml]

    print("job_inputs: " + str(job_inputs))
    job_inputs = download_job_inputs(job_inputs)
    print("updated job_inputs: " + str(job_inputs))
    postproc_cmdl.extend(get_opts(job_inputs))

    bcbio_yaml = job_inputs['bcbio_yaml']['filePath']
    print("bcbio yaml: " + bcbio_yaml)
    with open(bcbio_yaml) as f:
        conf_d = load_yaml(f)
    assert "upload" in conf_d, "upload not in bcbio_yaml: " + bcbio_yaml
    final_dir = conf_d["upload"]["dir"]
    if not final_dir.startswith('/'):
        print("final_dir " + final_dir + ' is not absolute')
        final_dir = '/dream_chr21/final'  # test data
    sample_section = conf_d["details"][0]["algorithm"]
    bed_files = [v for k, v in sample_section.iteritems() if k in ['variant_regions', 'sv_regions', 'coverage']]
    for bed_file in bed_files:
        print("Uploading BED file " + bed_file)
        if not bed_file.startswith('/'):
            bed_file = os.path.abspath(os.path.join(final_dir, bed_file))
            print("  path of the BED file is not absolute, changing to " + bed_file)
        copy_platform_folder_to_local(
            src_proj=os.environ['DX_PROJECT_CONTEXT_ID'],
            src_proj_fld=os.path.dirname(bed_file),
            dest_fld_prefix='/',
            exclude_func=lambda dxfile: dxfile['describe']['name'] != os.path.basename(bed_file))

    print('Copy final_dir ' + final_dir + ' locally for processing')
    copy_platform_folder_to_local(
        src_proj=os.environ['DX_PROJECT_CONTEXT_ID'],
        src_proj_fld=final_dir,
        dest_fld_prefix='/')

    config_dir = os.path.join(os.path.dirname(final_dir), "config")
    if not os.path.isdir(config_dir):
        print('Creating config dir ' + config_dir)
        os.makedirs(config_dir)
    else:
        print('config dir ' + config_dir + ' exists')
    print('Copy ' + bcbio_yaml + ' into ' + config_dir)
    config_bcbio_yaml = os.path.join(config_dir, os.path.basename(bcbio_yaml))
    os.rename(bcbio_yaml, config_bcbio_yaml)

    postproc_cmdl.append(final_dir)

    print('Running post-processing with the command: "' + " ".join(postproc_cmdl) + '"')
    subprocess.check_call(postproc_cmdl)

    ##### Output files ####
    report_file_links = []
    print('Uploading output files')

    # HTML reports
    multiqc_report = glob.glob(os.path.join(final_dir, "20??-??-??_*", "report.html"))
    if not multiqc_report:
        raise dxpy.exceptions.AppInternalError('Error: report.html not found for project ' + final_dir)
    multiqc_report = multiqc_report[0]
    print('MultiQC report: ' + multiqc_report)

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
    print('Other reports:')
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

    output = {'report_files': report_file_links}

    return output


dxpy.run()
