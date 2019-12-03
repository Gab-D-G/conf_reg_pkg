#!/usr/bin/env python3

import os
import sys
from utils import regress,tree_list,get_info_list
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
parser.add_argument('--commonspace_bold', type=bool,
                    help='If should run confound regression on a commonspace bold output.')
parser.add_argument('--highpass', type=float, default=None,
                    help='Specify highpass filter frequency.')
parser.add_argument('--lowpass', type=float, default=None,
                    help='Specify lowpass filter frequency.')
parser.add_argument('--smoothing_filter', type=float, default=0.3,
                    help='Specify smoothing filter size in mm.')
parser.add_argument('--TR', type=float,
                    default=1.0,
                    help='Repetition time')
parser.add_argument('--run_aroma', type=bool,
                    default=False,
                    help='Whether to run ICA AROMA or not.')
parser.add_argument('--aroma_dim', type=int,
                    default=0,
                    help='Can specify a number of dimension for MELODIC.')
parser.add_argument('--conf_list', type=str,
                    nargs="*",  # 0 or more values expected => creates a list
                    default=[],
                    help='list of regressors. Possible options: WM_signal,CSF_signal,aCompCor,global_signal,mot_6,mot_24, mean_FD')
parser.add_argument('--apply_scrubbing', type=bool,
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



# parse the command line
args = parser.parse_args()

rabies_out=args.rabies_out
out_dir=os.path.abspath(args.output_dir)
commonspace_bold=args.commonspace_bold
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


if commonspace_bold:
    bold_files=tree_list(os.path.abspath(rabies_out)+'/bold_datasink/commonspace_bold')
    brain_mask_files=tree_list(os.path.abspath(rabies_out)+'/bold_datasink/commonspace_bold_mask')
    csf_mask_files=tree_list(os.path.abspath(rabies_out)+'/bold_datasink/commonspace_CSF_mask')
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
                  name="info_node")
info_node.iterables = [('scan_info', scan_list)]

regress_node = pe.Node(Function(input_names=['scan_info', 'bold_files', 'brain_mask_files', 'confounds_files', 'csf_mask_files', 'FD_files', 'conf_list',
                                             'TR', 'lowpass', 'highpass', 'smoothing_filter', 'run_aroma', 'aroma_dim', 'apply_scrubbing', 'scrubbing_threshold', 'out_dir'],
                          output_names=['cleaned_img'],
                          function=regress),
                 name='regress')
regress_node.inputs.conf_list = conf_list
regress_node.inputs.TR = TR
regress_node.inputs.lowpass = lowpass
regress_node.inputs.highpass = highpass
regress_node.inputs.smoothing_filter = smoothing_filter
regress_node.inputs.run_aroma = run_aroma
regress_node.inputs.aroma_dim = aroma_dim
regress_node.inputs.apply_scrubbing = apply_scrubbing
regress_node.inputs.scrubbing_threshold = scrubbing_threshold
regress_node.inputs.out_dir = out_dir
regress_node.inputs.bold_files = bold_files
regress_node.inputs.brain_mask_files = brain_mask_files
regress_node.inputs.csf_mask_files = csf_mask_files
regress_node.inputs.confounds_files = confounds_files
regress_node.inputs.FD_files = FD_files


workflow = pe.Workflow(name='confound_regression')
workflow.connect([
    (info_node, regress_node, [
        ("scan_info", "scan_info"),
        ]),
    ])

workflow.base_dir = out_dir

workflow.config['execution'] = {'log_directory' : os.getcwd()}

workflow.run(plugin=plugin, plugin_args = {'max_jobs':50,'dont_resubmit_completed_jobs': True})
