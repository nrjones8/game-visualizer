import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import sklearn.cluster as clust
pd.set_option('max_columns', 50)


def analyze_from_csv(filename='data/rounds_two_three.csv'):
    df = pd.read_csv(filename, header=0, skipinitialspace=True)
    df['rank_diff'] = abs(df['away_rank'] - df['home_rank'])

    # Each row corresponds to one game timeline
    score_diff_mat = []
    # Matchups are tuples (away, home)
    matchups = []
    away_teams = []
    home_teams = []

    round_nums = []

    # Split into individual games -- this might be done better by melting 
    # the df?
    gb = df.groupby(['away', 'home'])
    for group, index in gb.groups.items():
        if np.nan not in group:
            print(group)
            score_diffs = list(df['diff_score'].iloc[index])

            score_diff_mat.append(score_diffs)
            matchups.append(group)
            round_nums.append(df['round_num'].iloc[index[0]])
            away_teams.append(group[0])
            home_teams.append(group[1])
            

    labels = cluster_time_series(score_diff_mat)
    #to_join = pd.DataFrame(labels, index=matchups, columns=['cluster_num'])
    to_merge = pd.DataFrame({
            'away' : away_teams, 
            'home' : home_teams,
            'cluster_num' : labels
            })
    print(to_merge)


    merged = df.merge(to_merge, on=['away', 'home'])
    merged.to_csv('data/with_clusters.csv')

def cluster_time_series(all_series, k=4):
    '''
    <all_series> is a list of lists, where each list
    corresponds to the diffs throughout a game
    '''
    c = clust.KMeans(n_clusters=k)
    c.fit(all_series)
    
    return c.labels_


if __name__ == '__main__':
    analyze_from_csv()