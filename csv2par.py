import pandas as pd
df=pd.read_csv('sub-jgrAesAWc11L_ses-1_run-1_confounds.csv')
new_df=pd.DataFrame(columns=['mov1','mov2','mov3','rot1','rot2','rot3'])
new_df['mov1']=df['mov1']
new_df['mov2']=df['mov2']
new_df['mov3']=df['mov3']
new_df['rot1']=df['rot1']
new_df['rot2']=df['rot2']
new_df['rot3']=df['rot3']
new_df.to_csv('sub-jgrAesAWc11L_ses-1_run-1_confounds.par', sep='\t', index=False, header=False)
