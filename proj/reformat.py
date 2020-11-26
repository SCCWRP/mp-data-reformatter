import pandas as pd
import glob, os, re
def reformat(orig_df):

    grouping_columns  = ['labid','sampleid','sizefraction', 'instrumenttype']
    
    orig_df.columns = [x.lower() for x in orig_df.columns]
    
    new = orig_df \
        .groupby(
            grouping_columns
        ) \
        .apply(
            lambda x: 
            x[
                list(set(x.columns) - set(grouping_columns))
            ] \
            .reset_index()
        ) \
        .reset_index() \
        .rename(
            columns = {f'level_{len(grouping_columns)}':'particleidnumber'}
        )
    
    new['particleidnumber'] = new['particleidnumber'] + 1

    new.insert(
        new.columns.tolist().index('particleid') + 1,
        "newparticleid",
        new \
        .apply(
            lambda x:
            '{}_{}_{}_{}'.format(
                x['sampleid'],
                x['instrumenttype'],
                'above500' if x['sizefraction'] == '>500 um'
                else x['sizefraction'].replace(" um",""),
                x['particleidnumber']
            )
            , axis = 1
        )
    )
    
    newphotoids = new \
        .groupby('photoid') \
        .apply(
            lambda x:
            "{}-{}".format(min(x['particleidnumber']), max(x['particleidnumber']))           
        ) \
        .reset_index() \
        .rename(columns = {0: "particlerange"})
    
    new = pd.merge(new,newphotoids, how = 'left', on = 'photoid')
   
    new.insert(
        new.columns.tolist().index('photoid') + 1,
        'newphotoid',
        new \
        .apply(
            lambda x:
            '{}_{}_{}_{}'.format(
                x['sampleid'],
                x['instrumenttype'],
                'above500' if x['sizefraction'] == '>500 um'
                else x['sizefraction'].replace(" um",""),
                x['particlerange']
            )
            , axis = 1
        )
    )
    
    #new.drop(['particlerange','particleidnumber','particleid','photoid','index'], axis = 1, inplace = True)
    new.rename(
        columns = {
            "photoid":"original_photoid",
            "particleid":"original_particleid",
            "newphotoid":"photoid",
            "newparticleid":"particleid",

        },
        inplace = True
    )

    # comparison_df will have the old particleid and photoids side by side
    comparison_df = new[orig_df.columns.tolist()]
    comparison_df.insert(
        comparison_df.columns.tolist().index("particleid"),
        "original_particleid",
        new.original_particleid
    )
    
    comparison_df.insert(
        comparison_df.columns.tolist().index("photoid"),
        "original_photoid",
        new.original_photoid
    )

    return \
        comparison_df, \
        new.drop(["original_photoid","original_particleid"], axis = 1)