This is a python package for confound regression of fMRI timeseries adapted to manage outputs from RABIES (https://github.com/CoBrALab/RABIES).

Confound regression approaches provided:
 * 6 rigid body parameters
 * 24 motion parameters (6 rigid, temporal derivative and the all parameters squared)
 * Framewise displacement
 * WM and CSF signals
 * aCompCorr
 * Global signal
 * ICA-AROMA


## /mod_ICA-AROMA:
  Consists of a modified version of the ICA-AROMA package (https://github.com/maartenmennes/ICA-AROMA), where the masks provided are already in the same space as the EPI, to allow the specification of rodent brain masks, and thus no registration is needed. A edge mask and outside mask are generated based on the provided brain mask.
