#!/usr/bin/env python

# Import required modules
from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import str
import os
import argparse
import subprocess
import ICA_AROMA_functions as aromafunc
import shutil
import classification_plots

# Change to script directory
cwd = os.path.realpath(os.path.curdir)
scriptDir = os.path.dirname(os.path.abspath(__file__))
os.chdir(scriptDir)

#-------------------------------------------- PARSER --------------------------------------------#

parser = argparse.ArgumentParser(description='Script to run ICA-AROMA v0.3 beta (\'ICA-based Automatic Removal Of Motion Artifacts\') on fMRI data. See the companion manual for further information.')

# Required options
reqoptions = parser.add_argument_group('Required arguments')
reqoptions.add_argument('-o', '-out', dest="outDir", required=True, help='Output directory name')

# Required options in non-Feat mode
nonfeatoptions = parser.add_argument_group('Required arguments - generic mode')
nonfeatoptions.add_argument('-i', '-in', dest="inFile", required=False, help='Input file name of fMRI data (.nii.gz)')
nonfeatoptions.add_argument('-mc', dest="mc", required=False, help='File name of the motion parameters obtained after motion realingment (e.g., FSL mcflirt). Note that the order of parameters does not matter, should your file not originate from FSL mcflirt. (e.g., /home/user/PROJECT/SUBJECT.feat/mc/prefiltered_func_data_mcf.par')
nonfeatoptions.add_argument('-m', '-mask', dest="mask", default="", help='File name of the mask to be used for MELODIC (denoising will be performed on the original/non-masked input data)')
nonfeatoptions.add_argument('-c', '-mask_csf', dest="mask_csf", default="", help='')

# Optional options
optoptions = parser.add_argument_group('Optional arguments')
optoptions.add_argument('-tr', dest="TR", help='TR in seconds', type=float)
optoptions.add_argument('-den', dest="denType", default="nonaggr", help='Type of denoising strategy: \'no\': only classification, no denoising; \'nonaggr\': non-aggresssive denoising (default); \'aggr\': aggressive denoising; \'both\': both aggressive and non-aggressive denoising (seperately)')
optoptions.add_argument('-md', '-meldir', dest="melDir", default="",help='MELODIC directory name, in case MELODIC has been run previously.')
optoptions.add_argument('-dim', dest="dim", default=0, help='Dimensionality reduction into #num dimensions when running MELODIC (default: automatic estimation; i.e. -dim 0)', type=int)
optoptions.add_argument('-ow', '-overwrite', dest="overwrite", action='store_true', help='Overwrite existing output', default=False)

print('\n------------------------------- RUNNING ICA-AROMA ------------------------------- ')
print('--------------- \'ICA-based Automatic Removal Of Motion Artifacts\' --------------- \n')


#--------------------------------------- PARSE ARGUMENTS ---------------------------------------#
args = parser.parse_args()

# Define variables based on the type of input (i.e. Feat directory or specific input arguments), and check whether the specified files exist.
cancel = False


inFile = args.inFile
mc = args.mc
melDir = args.melDir
mask_csf = args.mask_csf

# Check whether the files exist
if not inFile:
    print('No input file specified.')
else:
    if not os.path.isfile(inFile):
        print('The specified input file does not exist.')
        cancel = True
if not mc:
    print('No mc file specified.')
else:
    if not os.path.isfile(mc):
        print('The specified mc file does does not exist.')
        cancel = True

# Parse the arguments which do not depend on whether a Feat directory has been specified
outDir = args.outDir
dim = args.dim
denType = args.denType

# Check if the mask exists, when specified.
if args.mask:
    if not os.path.isfile(args.mask):
        print('The specified mask does not exist.')
        cancel = True

# Check if the type of denoising is correctly specified, when specified
if not (denType == 'nonaggr') and not (denType == 'aggr') and not (denType == 'both') and not (denType == 'no'):
    print('Type of denoising was not correctly specified. Non-aggressive denoising will be run.')
    denType = 'nonaggr'

# If the criteria for file/directory specifications have not been met. Cancel ICA-AROMA.
if cancel:
    print('\n----------------------------- ICA-AROMA IS CANCELED -----------------------------\n')
    exit()

#------------------------------------------- PREPARE -------------------------------------------#

# Define the FSL-bin directory
fslDir = os.path.join(os.environ["FSLDIR"], 'bin', '')

# Create output directory if needed
if os.path.isdir(outDir) and args.overwrite is False:
    print('Output directory', outDir, """already exists.
          AROMA will not continue.
          Rerun with the -overwrite option to explicitly overwrite existing output.""")
    exit()
elif os.path.isdir(outDir) and args.overwrite is True:
    print('Warning! Output directory', outDir, 'exists and will be overwritten.\n')
    shutil.rmtree(outDir)
    os.makedirs(outDir)
else:
    os.makedirs(outDir)

# Get TR of the fMRI data, if not specified
if args.TR:
    TR = args.TR
else:
    cmd = ' '.join([os.path.join(fslDir, 'fslinfo'),
                    inFile,
                    '| grep pixdim4 | awk \'{print $2}\''])
    TR = float(subprocess.getoutput(cmd))

# Check TR
if TR == 0:
    print('TR is zero. ICA-AROMA requires a valid TR and will therefore exit. Please check the header, or define the TR as an additional argument.\n----------------------------- ICA-AROMA IS CANCELED -----------------------------\n')
    exit()

# Define mask.
mask = os.path.join(outDir, 'mask.nii.gz')
shutil.copyfile(args.mask, mask)


#---------------------------------------- Run ICA-AROMA ----------------------------------------#

print('Step 1) MELODIC')
aromafunc.runICA(fslDir, inFile, outDir, melDir, mask, dim, TR)
melIC = os.path.join(outDir, 'melodic_IC_thr.nii.gz')

print('Step 2) Automatic classification of the components')

print('  - *modified version skips commonspace registration')

print('  - computing edge and out masks')
mask_edge = os.path.join(outDir, 'mask_edge.nii.gz')
mask_out = os.path.join(outDir, 'mask_out.nii.gz')
aromafunc.compute_edge_mask(mask,mask_edge, num_edge_voxels=1)
aromafunc.compute_out_mask(mask,mask_out)

print('  - extracting the CSF & Edge fraction features')
#modified inputs for the spatial features, by providing the required masks manually
edgeFract, csfFract = aromafunc.mod_feature_spatial(fslDir, outDir, melIC, mask_csf, mask_edge, mask_out)

print('  - extracting the Maximum RP correlation feature')
melmix = os.path.join(outDir, 'melodic.ica', 'melodic_mix')
maxRPcorr = aromafunc.feature_time_series(melmix, mc)

print('  - extracting the High-frequency content feature')
melFTmix = os.path.join(outDir, 'melodic.ica', 'melodic_FTmix')
HFC = aromafunc.feature_frequency(melFTmix, TR)

print('  - classification')
motionICs = aromafunc.classification(outDir, maxRPcorr, edgeFract, HFC, csfFract)
classification_plots.classification_plot(os.path.join(outDir, 'classification_overview.txt'),
                                         outDir)


if (denType != 'no'):
    print('Step 3) Data denoising')
    aromafunc.denoising(fslDir, inFile, outDir, melmix, denType, motionICs)

# Revert to old directory
os.chdir(cwd)

print('\n----------------------------------- Finished -----------------------------------\n')
