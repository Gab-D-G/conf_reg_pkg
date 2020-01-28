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
    from conf_reg.mod_ICA_AROMA.ICA_AROMA_functions import run_ICA_AROMA
    run_ICA_AROMA(os.path.abspath(outDir),os.path.abspath(inFile),mc=os.path.abspath(mc_file),TR=float(tr),mask=os.path.abspath(brain_mask),mask_csf=os.path.abspath(csf_mask),denType="nonaggr",melDir="",dim=str(aroma_dim),overwrite=True)
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

def scrubbing(img, FD_file, scrubbing_threshold,timeseries_interval):
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

    if not timeseries_interval=='all':
        lowcut=int(timeseries_interval.split(',')[0])
        highcut=int(timeseries_interval.split(',')[1])
        mask=mask[lowcut:highcut]

    masked_img=np.asarray(img.dataobj)[:,:,:,mask.astype(bool)]
    return nb.Nifti1Image(masked_img, img.affine, img.header)

def select_timeseries(bold_file,timeseries_interval):
    import os
    import numpy as np
    import nibabel as nb
    img=nb.load(bold_file)
    lowcut=int(timeseries_interval.split(',')[0])
    highcut=int(timeseries_interval.split(',')[1])
    bold_file=os.path.abspath('selected_timeseries.nii.gz')
    nb.Nifti1Image(np.asarray(img.dataobj)[:,:,:,lowcut:highcut], img.affine, img.header).to_filename(bold_file)
    return bold_file

def regress(scan_info,bold_file, brain_mask_file, confounds_file, csf_mask, FD_file, conf_list, TR, lowpass, highpass, smoothing_filter, run_aroma, aroma_dim, apply_scrubbing, scrubbing_threshold, timeseries_interval, out_dir):
    import os
    import pandas as pd
    import numpy as np
    import nibabel as nb
    import nilearn.image
    from conf_reg.utils import find_scans,scrubbing,exec_ICA_AROMA,csv2par

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
    aroma_out=out_dir
    if run_aroma:
        aroma_out=out_dir+'/%s_aroma' % (scan_info)
        smooth_path=os.path.abspath(out_dir+'/%s_smoothed.nii.gz' % (scan_info))
        cleaning_input.to_filename(smooth_path)
        cleaning_input=exec_ICA_AROMA(smooth_path, aroma_out, csv2par(confounds_file), brain_mask_file, csf_mask, TR, aroma_dim)
    if len(confounds_list)>0:
        confounds_array=np.transpose(np.asarray(confounds_list))
        if not timeseries_interval=='all':
            lowcut=int(timeseries_interval.split(',')[0])
            highcut=int(timeseries_interval.split(',')[1])
            confounds_array=confounds_array[lowcut:highcut,:]
        cleaned = nilearn.image.clean_img(cleaning_input, detrend=True, standardize=True, low_pass=lowpass, high_pass=highpass, confounds=confounds_array, t_r=TR, mask_img=brain_mask_file)
    else:
        cleaned = nilearn.image.clean_img(cleaning_input, detrend=True, standardize=True, low_pass=lowpass, high_pass=highpass, confounds=None, t_r=TR, mask_img=brain_mask_file)
    if apply_scrubbing:
        cleaned=scrubbing(cleaned, FD_file, scrubbing_threshold, timeseries_interval)
    cleaned_path=out_dir+'/'+scan_info+'_cleaned.nii.gz'
    cleaned.to_filename(cleaned_path)
    return cleaned_path, bold_file, aroma_out

def data_diagnosis(bold_file, cleaned_path, brain_mask_file, seed_list):
    import os
    import nibabel as nb
    import numpy as np
    mel_out=os.path.abspath('melodic.ica/')
    os.mkdir(mel_out)
    command='melodic -i %s -o %s -m %s --report' % (cleaned_path, mel_out, brain_mask_file)
    os.system(command)
    img=nb.load(bold_file)
    array=np.asarray(img.dataobj)
    mean=array.mean(axis=3)
    std=array.std(axis=3)
    tSNR=np.divide(mean, std)
    tSNR_file=os.path.abspath('tSNR.nii.gz')
    nb.Nifti1Image(tSNR, img.affine, img.header).to_filename(tSNR_file)

    def seed_based_FC(bold_file, brain_mask, seed):
        import os
        import nibabel as nb
        import numpy as np
        from nilearn.input_data import NiftiMasker
        img=nb.load(bold_file)
        array=np.asarray(img.dataobj)

        masker = NiftiMasker(mask_img=nb.load(seed), standardize=False, verbose=0)
        voxel_seed_timeseries = masker.fit_transform(bold_file) #extract the voxel timeseries within the mask
        seed_timeseries=np.mean(voxel_seed_timeseries, axis=1) #take the mean ROI timeseries

        mask_array=np.asarray(nb.load(brain_mask).dataobj)
        mask_vector=mask_array.reshape(-1)
        mask_indices=(mask_vector==True)

        timeseries_array=np.asarray(nb.load(bold_file).dataobj)
        sub_timeseries=np.zeros([mask_indices.sum(),timeseries_array.shape[3]])
        for t in range(timeseries_array.shape[3]):
            sub_timeseries[:,t]=(timeseries_array[:,:,:,t].reshape(-1))[mask_indices]

        #return a correlation between each row of X with y
        def vcorrcoef(X,y):
            Xm = np.reshape(np.mean(X,axis=1),(X.shape[0],1))
            ym = np.mean(y)
            r_num = np.sum((X-Xm)*(y-ym),axis=1)
            r_den = np.sqrt(np.sum((X-Xm)**2,axis=1)*np.sum((y-ym)**2))
            r = r_num/r_den
            return r
        corrs=vcorrcoef(sub_timeseries,seed_timeseries)

        mask_vector[mask_indices]=corrs
        corr_map=mask_vector.reshape(mask_array.shape)
        corr_map_file=os.path.abspath(os.path.basename(seed).split('.nii')[0]+'_corr_map.nii.gz')
        nb.Nifti1Image(corr_map, nb.load(brain_mask).affine, nb.load(brain_mask).header).to_filename(corr_map_file)
        return corr_map_file

    corr_map_list=[]
    for seed in seed_list:
        os.system('antsApplyTransforms -i %s -r %s -o %s -n GenericLabel' % (seed, brain_mask_file, os.path.abspath(os.path.basename(seed))))
        corr_map_file=seed_based_FC(cleaned_path, brain_mask_file, seed)
        corr_map_list.append(corr_map_file)

    return mel_out, tSNR_file, corr_map_list
