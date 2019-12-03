import os
import numpy as np
import nibabel as nb
import pandas as pd

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


def find_scans(scan_info, bold_files, brain_mask_files, confounds_files, csf_mask_files, FD_files):
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
    for file in FD_files:
        if scan_info in file:
            FD_file=file
            break
    return bold_file, brain_mask_file, confounds_file, csf_mask, FD_file

def exec_ICA_AROMA(inFile, outDir, mc_file, brain_mask, csf_mask, tr, aroma_dim):
    import os
    import conf_reg.utils
    dir_path = os.path.dirname(os.path.realpath(conf_reg.utils.__file__))
    ica_aroma_script_path=dir_path+'/mod_ICA_AROMA/ICA_AROMA.py'
    command='python %s -i %s -o %s -mc %s -m %s -c %s -tr %s -ow -dim %s' % (ica_aroma_script_path, os.path.abspath(inFile), os.path.abspath(outDir), os.path.abspath(mc_file), os.path.abspath(brain_mask), os.path.abspath(csf_mask), str(tr),str(aroma_dim),)
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
    out_confounds=os.path.abspath((os.path.basename(in_confounds).split('.')[0])+('.par'))
    new_df.to_csv(out_confounds, sep='\t', index=False, header=False)
    return out_confounds

def scrubbing(img, FD_file, scrubbing_threshold):
    '''
    Scrubbing based on FD: The frames that exceed the given threshold together with 1 back
    and 2 forward frames will be masked out from the data (as in Power et al. 2012)
    '''
    import numpy as np
    import nibabel as nb
    import pandas as pd
    mean_FD=pd.read_csv(FD_file).get('Mean')
    cutoff=np.asarray(mean_FD)>=scrubbing_threshold
    mask=np.ones(len(mean_FD))
    for i in range(len(mask)):
        if cutoff[i]:
            mask[i-1:i+2]=0
    masked_img=np.asarray(img.dataobj)[:,:,:,mask.astype(bool)]
    return nb.Nifti1Image(masked_img, img.affine, img.header)

def regress(scan_info, bold_files, brain_mask_files, confounds_files, csf_mask_files, FD_files, conf_list, TR, lowpass, highpass, smoothing_filter, run_aroma, aroma_dim, apply_scrubbing, scrubbing_threshold, out_dir):
    import os
    import pandas as pd
    import numpy as np
    import nilearn.image
    from conf_reg.utils import find_scans,scrubbing,exec_ICA_AROMA,csv2par


    bold_file, brain_mask_file, confounds_file, csf_mask, FD_file=find_scans(scan_info, bold_files, brain_mask_files, confounds_files, csf_mask_files, FD_files)
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
        elif conf=='mean_FD':
            mean_FD=pd.read_csv(FD_file).get('Mean')
            confounds_list.append(np.asarray(mean_FD))
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
        cleaning_input=exec_ICA_AROMA(smooth_path, out_dir+'/%s_aroma' % (scan_info), csv2par(confounds_file), brain_mask_file, csf_mask, TR, aroma_dim)
    if len(confounds_list)>0:
        confounds_array=np.transpose(np.asarray(confounds_list))
        cleaned = nilearn.image.clean_img(cleaning_input, detrend=True, standardize=True, low_pass=lowpass, high_pass=highpass, confounds=confounds_array, t_r=TR, mask_img=brain_mask_file)
    else:
        cleaned = nilearn.image.clean_img(cleaning_input, detrend=True, standardize=True, low_pass=lowpass, high_pass=highpass, confounds=None, t_r=TR, mask_img=brain_mask_file)
    if apply_scrubbing:
        cleaned=scrubbing(cleaned, FD_file, scrubbing_threshold)
    cleaned_path=out_dir+'/'+scan_info+'_cleaned.nii.gz'
    cleaned.to_filename(cleaned_path)
    return cleaned_path
