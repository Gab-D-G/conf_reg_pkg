#!/usr/bin/env python3
import os
import sys
from utils import regress,tree_list,get_info_list,find_scans, data_diagnosis, select_timeseries
import argparse

"""Build parser object"""
parser = argparse.ArgumentParser(
    description="""Confound regression package adapted to automatized confound regression applied
    on outputs from RABIES. Smoothing is applied first, followed by ICA-AROMA, detrending, then
    regression of confound timeseries orthogonal to the application of temporal filters
    (nilearn.clean_img, Lindquist 2018), and finally standardization of timeseries. The corrections
    follow user specifications.""",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('rabies_out', type=str,
                    help='path to RABIES output directory with the datasinks.')
parser.add_argument('output_dir', type=str,
                    help='will drop corrected image in that folder')
parser.add_argument('--commonspace_bold', dest='commonspace_bold', action='store_true',
                    help='If should run confound regression on a commonspace bold output.')
parser.add_argument('--bold_only', dest='bold_only', action='store_true',
                    help='If RABIES was run with the bold_only option.')
parser.add_argument('--highpass', type=float, default=None,
                    help='Specify highpass filter frequency.')
parser.add_argument('--lowpass', type=float, default=None,
                    help='Specify lowpass filter frequency.')
parser.add_argument('--smoothing_filter', type=float, default=0.3,
                    help='Specify smoothing filter size in mm.')
parser.add_argument('--TR', type=float,
                    default=1.0,
                    help='Repetition time')
parser.add_argument('--run_aroma', dest='run_aroma', action='store_true',
                    default=False,
                    help='Whether to run ICA AROMA or not.')
parser.add_argument('--aroma_dim', type=int,
                    default=0,
                    help='Can specify a number of dimension for MELODIC.')
parser.add_argument('--conf_list', type=str,
                    nargs="*",  # 0 or more values expected => creates a list
                    default=[],
                    help='list of regressors. Possible options: WM_signal,CSF_signal,vascular_signal,aCompCor,global_signal,mot_6,mot_24, mean_FD')
parser.add_argument('--apply_scrubbing', dest='apply_scrubbing', action='store_true',
                    default=False,
                    help="""Whether to apply scrubbing or not. A temporal mask will be generated based on the FD threshold.
                    The frames that exceed the given threshold together with 1 back and 2 forward frames will be masked out
                    from the data after the application of all other confound regression steps (as in Power et al. 2012).""")
parser.add_argument('--scrubbing_threshold', type=float,
                    default=0.1,
                    help='Scrubbing threshold for the mean framewise displacement in mm? (averaged across the brain mask) to select corrupted volumes.')
parser.add_argument("-p", "--plugin", type=str, default='Linear',
                    help="Specify the nipype plugin for workflow execution. Consult nipype plugin documentation for detailed options."
                         " Linear, MultiProc, SGE and SGEGraph have been tested.")
parser.add_argument("--min_proc", type=int, default=1,
                    help="For parallel processing, specify the minimal number of nodes to be assigned.")
parser.add_argument('--timeseries_interval', type=str, default='all',
                    help='Specify which timepoints to keep. e.g. "0,80".')
parser.add_argument('--diagnosis_output', dest='diagnosis_output', action='store_true',
                    default=False,
                    help="Run a diagnosis for each image by computing melodic-ICA on the corrected timeseries,"
                         "and compute a tSNR map from the input uncorrected image.")
parser.add_argument('--seed_list', type=str,
                    nargs="*",  # 0 or more values expected => creates a list
                    default=[],
                    help='Can provide a list of seed .nii images that will be used to evaluate seed-based correlation maps during data diagnosis.')


# parse the command line
args = parser.parse_args()

rabies_out=args.rabies_out
out_dir=os.path.abspath(args.output_dir)
commonspace_bold=args.commonspace_bold
bold_only=args.bold_only
lowpass=args.lowpass
highpass=args.highpass
smoothing_filter=args.smoothing_filter
run_aroma=args.run_aroma
aroma_dim=args.aroma_dim
conf_list=args.conf_list
TR=args.TR
apply_scrubbing=args.apply_scrubbing
scrubbing_threshold=args.scrubbing_threshold
plugin=args.plugin
timeseries_interval=args.timeseries_interval
diagnosis_output=args.diagnosis_output
seed_list=args.seed_list
min_proc=args.min_proc

if bold_only:
    bold_files=tree_list(os.path.abspath(rabies_out)+'/bold_datasink/corrected_bold')
    brain_mask_files=tree_list(os.path.abspath(rabies_out)+'/bold_datasink/bold_brain_mask')
    csf_mask_files=tree_list(os.path.abspath(rabies_out)+'/bold_datasink/bold_CSF_mask')
else:
    if commonspace_bold:
        bold_files=tree_list(os.path.abspath(rabies_out)+'/bold_datasink/commonspace_bold')
        brain_mask_files=tree_list(os.path.abspath(rabies_out)+'/bold_datasink/commonspace_bold_mask')
        csf_mask_files=tree_list(os.path.abspath(rabies_out)+'/bold_datasink/commonspace_bold_CSF_mask')
    else:
        bold_files=tree_list(os.path.abspath(rabies_out)+'/bold_datasink/corrected_bold')
        brain_mask_files=tree_list(os.path.abspath(rabies_out)+'/bold_datasink/bold_brain_mask')
        csf_mask_files=tree_list(os.path.abspath(rabies_out)+'/bold_datasink/bold_CSF_mask')

confounds_files=tree_list(os.path.abspath(rabies_out)+'/confounds_datasink/confounds_csv')
FD_files=tree_list(os.path.abspath(rabies_out)+'/confounds_datasink/FD_csv')

scan_list=get_info_list(bold_files)


#execute within a nipype workflow
from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces.utility import Function

info_node = pe.Node(niu.IdentityInterface(fields=['scan_info']),
                  name="info_node", mem_gb=1)
info_node.iterables = [('scan_info', scan_list)]


find_scans_node = pe.Node(Function(input_names=['scan_info', 'bold_files', 'brain_mask_files', 'confounds_files', 'csf_mask_files', 'FD_files'],
                          output_names=['bold_file', 'brain_mask_file', 'confounds_file', 'csf_mask', 'FD_file'],
                          function=find_scans),
                 name='find_scans', mem_gb=1)
find_scans_node.inputs.bold_files = bold_files
find_scans_node.inputs.brain_mask_files = brain_mask_files
find_scans_node.inputs.csf_mask_files = csf_mask_files
find_scans_node.inputs.confounds_files = confounds_files
find_scans_node.inputs.FD_files = FD_files

regress_node = pe.Node(Function(input_names=['scan_info','bold_file', 'brain_mask_file', 'confounds_file', 'csf_mask', 'FD_file', 'conf_list',
                                             'TR', 'lowpass', 'highpass', 'smoothing_filter', 'run_aroma', 'aroma_dim', 'apply_scrubbing', 'scrubbing_threshold', 'timeseries_interval', 'out_dir'],
                          output_names=['cleaned_path', 'bold_file', 'aroma_out'],
                          function=regress),
                 name='regress', mem_gb=1)
regress_node.inputs.conf_list = conf_list
regress_node.inputs.TR = TR
regress_node.inputs.lowpass = lowpass
regress_node.inputs.highpass = highpass
regress_node.inputs.smoothing_filter = smoothing_filter
regress_node.inputs.run_aroma = run_aroma
regress_node.inputs.aroma_dim = aroma_dim
regress_node.inputs.apply_scrubbing = apply_scrubbing
regress_node.inputs.scrubbing_threshold = scrubbing_threshold
regress_node.inputs.timeseries_interval = timeseries_interval
regress_node.inputs.out_dir = out_dir

workflow = pe.Workflow(name='confound_regression')
workflow.connect([
    (info_node, find_scans_node, [
        ("scan_info", "scan_info"),
        ]),
    (info_node, regress_node, [
        ("scan_info", "scan_info"),
        ]),
    (find_scans_node, regress_node, [
        ("brain_mask_file", "brain_mask_file"),
        ("confounds_file", "confounds_file"),
        ("csf_mask", "csf_mask"),
        ("FD_file", "FD_file"),
        ]),
    ])


if not timeseries_interval=='all':
    select_timeseries_node = pe.Node(Function(input_names=['bold_file', 'timeseries_interval'],
                              output_names=['bold_file'],
                              function=select_timeseries),
                     name='select_timeseries', mem_gb=1)
    select_timeseries_node.inputs.timeseries_interval = timeseries_interval

    workflow.connect([
        (find_scans_node, select_timeseries_node, [
            ("bold_file", "bold_file"),
            ]),
        (select_timeseries_node, regress_node, [
            ("bold_file", "bold_file"),
            ]),
        ])
else:
    workflow.connect([
        (find_scans_node, regress_node, [
            ("bold_file", "bold_file"),
            ]),
        ])


if diagnosis_output:
    data_diagnosis_node = pe.Node(Function(input_names=['bold_file', 'cleaned_path', 'brain_mask_file', 'seed_list'],
                              output_names=['mel_out','tSNR_file','corr_map_list'],
                              function=data_diagnosis),
                     name='data_diagnosis', mem_gb=1)
    data_diagnosis_node.inputs.seed_list=seed_list
    workflow.connect([
        (find_scans_node, data_diagnosis_node, [
            ("brain_mask_file", "brain_mask_file"),
            ]),
        (regress_node, data_diagnosis_node, [
            ("cleaned_path", "cleaned_path"),
            ("bold_file", "bold_file"),
            ]),
        ])


workflow.base_dir = out_dir

workflow.config['execution'] = {'log_directory' : os.getcwd()}

print('Running main workflow with %s plugin.' % plugin)
#execute workflow, with plugin_args limiting the cluster load for parallel execution
workflow.run(plugin=plugin, plugin_args = {'max_jobs':50,'dont_resubmit_completed_jobs': True, 'qsub_args': '-pe smp %s' % (int(min_proc))})
