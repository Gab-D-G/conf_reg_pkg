import os
import pandas as pd
import numpy as np
import nilearn.image
import sys

import argparse
# defined command line options

parser = argparse.ArgumentParser()

parser.add_argument('file_path', type=str,
                    help='path to files')
parser.add_argument('sub', type=str,
                    help='sub_id')
parser.add_argument('output_dir', type=str,
                    help='will drop corrected image in that folder')
parser.add_argument('--TR', type=float,
                    default=1.0,
                    help='Repetition time')
parser.add_argument('--conf_list', type=str,
                    nargs="*",  # 0 or more values expected => creates a list
                    default=[],
                    help='list of regressors. Possible options: WM_signal,CSF_signal,aCompCor,global_signal,mot_6,mot_24')


# parse the command line
args = parser.parse_args()

file_path=args.file_path
sub=args.sub
out_dir=args.output_dir
conf_list=args.conf_list
TR=args.TR

bold_file=file_path+'/%s_ses-1_run-1_combined.nii.gz' % (sub)
confounds_file=file_path+'/%s_ses-1_run-1_confounds.csv' % (sub)
brain_mask_file=file_path+'/%s_ses-1_run-1_brain_mask.nii.gz' % (sub)

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

confounds_array=np.transpose(np.asarray(confounds_list))

#including detrending, standardization, highpass at 0.01Hz, and smoothing at 0.3mm
smoothed=nilearn.image.smooth_img(bold_file, 0.3)
cleaned = nilearn.image.clean_img(smoothed, detrend=True, standardize=True, high_pass=0.01, confounds=confounds_array, t_r=TR, mask_img=brain_mask_file)
cleaned_path=out_dir+'/'+sub+'_cleaned.nii.gz'
cleaned.to_filename(cleaned_path)
