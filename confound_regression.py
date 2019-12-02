import os
import sys

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
parser.add_argument('--conf_list', type=str,
                    nargs="*",  # 0 or more values expected => creates a list
                    default=[],
                    help='list of regressors. Possible options: WM_signal,CSF_signal,aCompCor,global_signal,mot_6,mot_24')
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
conf_list=args.conf_list
TR=args.TR
plugin=args.plugin

def tree_list(dirName):
    # Get the list of all files in directory tree at given path
    listOfFiles = list()
    for (dirpath, dirnames, filenames) in os.walk(dirName):
        listOfFiles += [os.path.join(dirpath, file) for file in filenames]
    return listOfFiles

def get_info_list(file_list):
    info_list=[]
    for file in file_list:
        basename=os.path.basename(file)
        file_info=basename.split('_run-')[0]+'_run-'+basename.split('_run-')[1][0]
        info_list.append(file_info)

    return info_list


if commonspace_bold:
    bold_files=tree_list(os.path.abspath(rabies_out)+'/bold_datasink/commonspace_bold')
    brain_mask_files=tree_list(os.path.abspath(rabies_out)+'/bold_datasink/commonspace_bold_mask')
    csf_mask_files=tree_list(os.path.abspath(rabies_out)+'/bold_datasink/commonspace_CSF_mask')
else:
    bold_files=tree_list(os.path.abspath(rabies_out)+'/bold_datasink/corrected_bold')
    brain_mask_files=tree_list(os.path.abspath(rabies_out)+'/bold_datasink/bold_brain_mask')
    csf_mask_files=tree_list(os.path.abspath(rabies_out)+'/bold_datasink/bold_CSF_mask')

confounds_files=tree_list(os.path.abspath(rabies_out)+'/confounds_datasink/confounds_csv')

scan_list=get_info_list(bold_files)

def regress(scan_info, bold_files, brain_mask_files, confounds_files, csf_mask_files, conf_list, TR, lowpass, highpass, smoothing_filter, run_aroma, out_dir):
    import os
    import pandas as pd
    import numpy as np
    import nilearn.image

    def find_scans(scan_info, bold_files, brain_mask_files, confounds_files, csf_mask_files):
        for file in bold_files:
            if scan_info in file:
                bold_file=file
                break
        for file in brain_mask_files:
            if scan_info in file:
                brain_mask_file=file
                break
        for file in confounds_files:
            if scan_info in file:
                confounds_file=file
                break
        for file in csf_mask_files:
            if scan_info in file:
                csf_mask=file
                break
        return bold_file, brain_mask_file, confounds_file, csf_mask

    def exec_ICA_AROMA(inFile, outDir, mc_file, brain_mask, csf_mask, tr):
        import os
        #import confound_regression
        #dir_path = os.path.dirname(os.path.realpath(confound_regression.__file__))
        #ica_aroma_script_path=dir_path+'/mod_ICA_AROMA/ICA_AROMA.py'
        command='python /home/gabriel/Desktop/software/conf_reg_pkg/mod_ICA_AROMA/ICA_AROMA.py -i %s -o %s -mc %s -m %s -c %s -tr %s -ow' % (os.path.abspath(inFile), os.path.abspath(outDir), os.path.abspath(mc_file), os.path.abspath(brain_mask), os.path.abspath(csf_mask), str(tr),)
        print(command)
        os.system(command)
        return os.path.abspath(outDir+'/denoised_func_data_nonaggr.nii.gz')

    def csv2par(in_confounds):
        import pandas as pd
        df=pd.read_csv(in_confounds)
        new_df=pd.DataFrame(columns=['mov1','mov2','mov3','rot1','rot2','rot3'])
        new_df['mov1']=df['mov1']
        new_df['mov2']=df['mov2']
        new_df['mov3']=df['mov3']
        new_df['rot1']=df['rot1']
        new_df['rot2']=df['rot2']
        new_df['rot3']=df['rot3']
        out_confounds=(in_confounds.split('.')[0])+('.par')
        new_df.to_csv(out_confounds, sep='\t', index=False, header=False)
        return out_confounds


    bold_file, brain_mask_file, confounds_file, csf_mask=find_scans(scan_info, bold_files, brain_mask_files, confounds_files, csf_mask_files)
    confounds=pd.read_csv(confounds_file)
    keys=confounds.keys()
    confounds_list=[]
    for conf in conf_list:
        if conf=='mot_6':
            motion_keys = ['mov1', 'mov2', 'mov3', 'rot1', 'rot2', 'rot3']
            for mov in motion_keys:
                confounds_list.append(np.asarray(confounds.get(mov)))
        elif conf=='mot_24':
            motion_keys = [s for s in keys if "rot" in s or "mov" in s]
            for mov in motion_keys:
                confounds_list.append(np.asarray(confounds.get(mov)))
        elif conf=='aCompCor':
            aCompCor_keys = [s for s in keys if "aCompCor" in s]
            print('Applying aCompCor with '+len(aCompCor_keys)+' components.')
            for aCompCor in aCompCor_keys:
                confounds_list.append(np.asarray(confounds.get(aCompCor)))
        else:
            confounds_list.append(np.asarray(confounds.get(conf)))

    '''
    what would be nice would be to have a print out of the variance explained for each regressor, to confirm it accounts for something
    '''

    #including detrending, standardization
    cleaning_input=nilearn.image.smooth_img(bold_file, smoothing_filter)
    if run_aroma:
        smooth_path=os.path.abspath(out_dir+'/%s_smoothed.nii.gz' % (scan_info))
        cleaning_input.to_filename(smooth_path)
        cleaning_input=exec_ICA_AROMA(smooth_path, out_dir+'/%s_aroma' % (scan_info), csv2par(confounds_file), brain_mask_file, csf_mask, TR)
    if len(confounds_list)>0:
        confounds_array=np.transpose(np.asarray(confounds_list))
        cleaned = nilearn.image.clean_img(cleaning_input, detrend=True, standardize=True, low_pass=lowpass, high_pass=highpass, confounds=confounds_array, t_r=TR, mask_img=brain_mask_file)
    else:
        cleaned = nilearn.image.clean_img(cleaning_input, detrend=True, standardize=True, low_pass=lowpass, high_pass=highpass, confounds=None, t_r=TR, mask_img=brain_mask_file)
    cleaned_path=out_dir+'/'+scan_info+'_cleaned.nii.gz'
    cleaned.to_filename(cleaned_path)
    return cleaned_path

#execute within a nipype workflow
from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces.utility import Function

info_node = pe.Node(niu.IdentityInterface(fields=['scan_info']),
                  name="info_node")
info_node.iterables = [('scan_info', scan_list)]

regress_node = pe.Node(Function(input_names=['scan_info', 'bold_files', 'brain_mask_files', 'confounds_files', 'csf_mask_files', 'conf_list', 'TR', 'lowpass', 'highpass', 'smoothing_filter', 'run_aroma', 'out_dir'],
                          output_names=['cleaned_img'],
                          function=regress),
                 name='regress')
regress_node.inputs.conf_list = conf_list
regress_node.inputs.TR = TR
regress_node.inputs.lowpass = lowpass
regress_node.inputs.highpass = highpass
regress_node.inputs.smoothing_filter = smoothing_filter
regress_node.inputs.run_aroma = run_aroma
regress_node.inputs.out_dir = out_dir
regress_node.inputs.bold_files = bold_files
regress_node.inputs.brain_mask_files = brain_mask_files
regress_node.inputs.csf_mask_files = csf_mask_files
regress_node.inputs.confounds_files = confounds_files


workflow = pe.Workflow(name='confound_regression')
workflow.connect([
    (info_node, regress_node, [
        ("scan_info", "scan_info"),
        ]),
    ])

workflow.base_dir = out_dir

workflow.config['execution'] = {'log_directory' : os.getcwd()}

workflow.run(plugin=plugin, plugin_args = {'max_jobs':50,'dont_resubmit_completed_jobs': True})
