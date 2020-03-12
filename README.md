This is a python package for confound regression of fMRI timeseries adapted to manage outputs from RABIES (https://github.com/CoBrALab/RABIES).
## Features
Confound regression approaches provided:
 * 6 rigid body parameters
 * 24 motion parameters (6 rigid, temporal derivative and the all parameters squared)
 * Framewise displacement
 * WM and CSF signals
 * vascular signals
 * aCompCorr
 * Global signal
 * ICA-AROMA
 * Scrubbing
Filters (from https://nilearn.github.io/modules/generated/nilearn.image.clean_img.html):
 * highpass
 * lowpass
 * spatial smoothing

<br/>
Diagnosis output option (--diagnosis_output): allows to generate tSNR, ICA components from FSL's MELODIC (https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/MELODIC) and seed-based connectivity maps (from seeds provided by the user) for every individual scans for observation purposes. This allows to establish the quality of the data and presence of confounds at the individual scan level.

## Command Line Interface
```
usage: confound_regression.py [-h] [--commonspace_bold] [--bold_only]
                              [--highpass HIGHPASS] [--lowpass LOWPASS]
                              [--smoothing_filter SMOOTHING_FILTER] [--TR TR]
                              [--run_aroma] [--aroma_dim AROMA_DIM]
                              [--conf_list [CONF_LIST [CONF_LIST ...]]]
                              [--apply_scrubbing]
                              [--scrubbing_threshold SCRUBBING_THRESHOLD]
                              [-p PLUGIN] [--min_proc MIN_PROC]
                              [--timeseries_interval TIMESERIES_INTERVAL]
                              [--diagnosis_output]
                              [--seed_list [SEED_LIST [SEED_LIST ...]]]
                              rabies_out output_dir

Confound regression package adapted to automatized confound regression applied
on outputs from RABIES. Smoothing is applied first, followed by ICA-AROMA,
detrending, then regression of confound timeseries orthogonal to the
application of temporal filters (nilearn.clean_img, Lindquist 2018), and
finally standardization of timeseries. The corrections follow user
specifications.

positional arguments:
  rabies_out            path to RABIES output directory with the datasinks.
  output_dir            will drop corrected image in that folder

optional arguments:
  -h, --help            show this help message and exit
  --commonspace_bold    If should run confound regression on a commonspace
                        bold output. (default: False)
  --bold_only           If RABIES was run with the bold_only option. (default:
                        False)
  --highpass HIGHPASS   Specify highpass filter frequency. (default: None)
  --lowpass LOWPASS     Specify lowpass filter frequency. (default: None)
  --smoothing_filter SMOOTHING_FILTER
                        Specify smoothing filter size in mm. (default: 0.3)
  --TR TR               Repetition time (default: 1.0)
  --run_aroma           Whether to run ICA AROMA or not. (default: False)
  --aroma_dim AROMA_DIM
                        Can specify a number of dimension for MELODIC.
                        (default: 0)
  --conf_list [CONF_LIST [CONF_LIST ...]]
                        list of regressors. Possible options: WM_signal,CSF_si
                        gnal,vascular_signal,aCompCor,global_signal,mot_6,mot_
                        24, mean_FD (default: [])
  --apply_scrubbing     Whether to apply scrubbing or not. A temporal mask
                        will be generated based on the FD threshold. The
                        frames that exceed the given threshold together with 1
                        back and 2 forward frames will be masked out from the
                        data after the application of all other confound
                        regression steps (as in Power et al. 2012). (default:
                        False)
  --scrubbing_threshold SCRUBBING_THRESHOLD
                        Scrubbing threshold for the mean framewise
                        displacement in mm? (averaged across the brain mask)
                        to select corrupted volumes. (default: 0.1)
  -p PLUGIN, --plugin PLUGIN
                        Specify the nipype plugin for workflow execution.
                        Consult nipype plugin documentation for detailed
                        options. Linear, MultiProc, SGE and SGEGraph have been
                        tested. (default: Linear)
  --min_proc MIN_PROC   For parallel processing, specify the minimal number of
                        nodes to be assigned. (default: 1)
  --timeseries_interval TIMESERIES_INTERVAL
                        Specify which timepoints to keep. e.g. "0,80".
                        (default: all)
  --diagnosis_output    Run a diagnosis for each image by computing melodic-
                        ICA on the corrected timeseries,and compute a tSNR map
                        from the input uncorrected image. (default: False)
  --seed_list [SEED_LIST [SEED_LIST ...]]
                        Can provide a list of seed .nii images that will be
                        used to evaluate seed-based correlation maps during
                        data diagnosis. (default: [])
```

## Execution syntax
```bash
  confound_regression.py /rabies_outputs /output_directory \
  --commonspace_bold --conf_list WM_signal CSF_signal vascular_signal mot_24 --highpass 0.01 \
  --diagnosis_output --seed_list /seeds/left_retrosplenial.nii.gz /seeds/left_somatosensory.nii.gz \
  -p Linear
```
### Running interactively within a container
Singularity execution
```bash
  singularity run -B /local_rabies_output_folder_path:/rabies_outputs:ro \
  -B /local_output_folder_path:/output_directory \
  /path_to_singularity_image/conf_reg.sif /rabies_outputs /output_directory \
  --execution_specifications
```
Docker execution
```bash
  docker run -it --rm \
	-v /local_rabies_output_folder_path:/rabies_outputs:ro \
	-v /local_output_folder_path:/output_directory \
	gabdesgreg/conf_reg /path_to_singularity_image/conf_reg.sif /rabies_outputs /output_directory \
  --execution_specifications
```
## Outputs
Cleaned EPI timeseries: /output_directory/sub-{sub_id}_ses-{ses_num}_run-{run_num}_cleaned.nii.gz
<br/>
Diagnosis outputs: /output_directory/confound_regression/_scan_info_sub-{sub_id}_ses-{ses_num}_run-{run_num}/data_diagnosis/

## /mod_ICA-AROMA:
  Consists of a modified version of the ICA-AROMA package (https://github.com/maartenmennes/ICA-AROMA), where the masks provided are already in the same space as the EPI, to allow the specification of rodent brain masks, and thus no registration is needed. An edge mask and outside mask are generated based on the provided brain mask.
