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

OPT_CMD = {
}

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
        if f_dx is not None:
            f_path = f_dx.name
            dxpy.download_dxfile(f_dx, f_path)
            input_dict[inp_name] = {
                "dxFileObj": f_dx,
                "filePath": f_path
            }


def create_cmd_opt_str(updated_input_dict):
    """Create shell string for subrocess usage"""
    cmd_opt = []
    for inp, val in updated_input_dict.iteritems():
        opt_str = OPT_CMD.get(inp)
        if opt_str is None:
            continue
        param = val.get('filePath') if type(val) is dict else val
        cmd_opt.append(opt_str.format(param=param))
    return " ".join(cmd_opt)


@dxpy.entry_point('main')
def main(**job_inputs):
    # Biolerplate for debugging and ngs_report scripts
    # data_dir = os.path.join(os.path.expanduser('~'), 'Data')
    # os.mkdir(data_dir)
    # Download inputs
    download_job_inputs(job_inputs)

    bcbio_postproc_cmd = [
        'source', '/miniconda/bin/activate', 'ngs_reporting', '&&',
        'bcbio_postproc', '-d', '--sys-cfg', '/miniconda/reference_data/system_info_Nexus_Test.yaml']

    bcbio_yaml = job_inputs['bcbio_yaml']['filePath']
    print('Bcbio yaml:', bcbio_yaml)
    bcbio_dir = os.path.dirname(os.path.dirname(bcbio_yaml))
    print('Bcbio directory:', bcbio_dir)
    run_cmdl = 'bcbio_postproc -d ' + create_cmd_opt_str(job_inputs)
    run_cmdl += ' ' + bcbio_dir

    print('Runing post-processing with the command: "' + run_cmdl + '"')
    subprocess.check_call(run_cmdl.split())

    # Output files
    output = {}
    bcbio_proj = BcbioProject()
    bcbio_proj.load_from_bcbio_dir(bcbio_dir)
    report_path = bcbio_proj.find_multiqc_report()
    if not report_path:
        print('Error: not report.html found for project ' + bcbio_dir)
    else:
        output['html_report'] = dxpy.dxlink(dxpy.upload_local_file(report_path))

    return output


dxpy.run()
