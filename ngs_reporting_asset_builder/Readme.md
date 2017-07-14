Asset Builder
====================

Creates assets, but without specifying a full dxasset.json, etc. This makes it
a little easier to create an asset, but you trade off some reproducibility.

To use:

1. Run with the --allow-ssh flag

```dx run adhoc_asset_builder --allow-ssh```

2. SSH into the job

```dx ssh job-xxxx```

3. Do something useful

```sudo pip install numpy```

4. Run create-asset

```create-asset --asset_name numpy_asset --asset_version 1.0.0```

5. Logout and terminate the job

An asset will have been created in the project that you can refer to by record
id.

Sample commands:
`bcbio_postproc /home/dnanexus/NGS_Reporting/NGS_Reporting_TestData/results/bcbio_postproc/rnaseq -d -t 1`
`bcbio_postproc /home/dnanexus/NGS_Reporting/NGS_Reporting_TestData/results/bcbio_postproc/rnaseq -d -t 1 --sys-cfg az/configs/system_info_local.yaml`
