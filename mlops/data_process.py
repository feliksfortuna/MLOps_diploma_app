import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, OrdinalEncoder

merged_data = pd.read_csv('/home/bsc/MLOps_diploma_app/common/final_data.csv')

def split_test_train_data(index):
    train_data = merged_data[merged_data['year'] < 2024]
    test_data = merged_data[merged_data['year'] == 2024]
    
    unique_race_names = test_data['name'].unique()
    races_to_move = unique_race_names[:index+1]
    
    race_data_to_move = test_data[test_data['name'].isin(races_to_move)]
    train_data = pd.concat([train_data, race_data_to_move], ignore_index=True)
    test_data = test_data[~test_data['name'].isin(races_to_move)].reset_index(drop=True)
    
    return train_data, test_data

def preprocess_data(index):
    # Define feature groups
    race_numerical = ['distance', 'vertical_meters', 'speed', 'year', 'score', 'quality', 'ranking']
    race_categorical = ['name']
    rider_numerical = ['weight', 'height', 'one_day', 'gc', 'tt', 'sprint', 'climber', 'hills', 'age']
    rider_categorical_low = ['speciality']
    rider_categorical_high = ['nationality', 'team', 'rider_name']

    train_data, test_data = split_test_train_data(index)

    max_riders_train = train_data.groupby(['name', 'year']).size().max()
    max_riders_test = test_data.groupby(['name', 'year']).size().max()
    max_riders = max(max_riders_train, max_riders_test)

    # Create and fit preprocessing pipelines
    race_numeric_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', MinMaxScaler())
    ], memory=None)
    race_categorical_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='constant', fill_value='Unknown')),
        ('onehot', OneHotEncoder(drop='first', sparse_output=False, handle_unknown='ignore'))
    ], memory=None)
    rider_numeric_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', MinMaxScaler())
    ], memory=None)
    rider_categorical_low_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='constant', fill_value='Unknown')),
        ('onehot', OneHotEncoder(drop='first', sparse_output=False, handle_unknown='ignore'))
    ], memory=None)
    rider_categorical_high_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='constant', fill_value='Unknown')),
        ('ordinal', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1))
    ], memory=None)

    # Fit pipelines on training data
    race_numeric_pipeline.fit(train_data[race_numerical])
    race_categorical_pipeline.fit(train_data[race_categorical])
    rider_numeric_pipeline.fit(train_data[rider_numerical])
    rider_categorical_low_pipeline.fit(train_data[rider_categorical_low])
    rider_categorical_high_pipeline.fit(train_data[rider_categorical_high])

    # Process test data only
    races_test = []
    rider_names_test = []

    for (race_name, year), group in test_data.groupby(['name', 'year']):
        try:
            # Process features
            race_num_processed = race_numeric_pipeline.transform(group[race_numerical].iloc[[0]])
            race_cat_processed = race_categorical_pipeline.transform(group[race_categorical].iloc[[0]])
            rider_num_processed = rider_numeric_pipeline.transform(group[rider_numerical])
            rider_cat_low_processed = rider_categorical_low_pipeline.transform(group[rider_categorical_low])
            rider_cat_high_processed = rider_categorical_high_pipeline.transform(group[rider_categorical_high])

            race_features = np.hstack((race_num_processed, race_cat_processed))
            rider_features = np.hstack((rider_num_processed, rider_cat_low_processed, rider_cat_high_processed))

            # Pad rider features
            n_riders = rider_features.shape[0]
            if n_riders < max_riders:
                padded_rider_features = np.pad(
                    rider_features,
                    ((0, max_riders - n_riders), (0, 0)),
                    mode='constant',
                    constant_values=0
                )
            else:
                padded_rider_features = rider_features[:max_riders, :]

            # Create feature matrix
            feature_matrix = np.hstack((
                np.tile(race_features, (max_riders, 1)),
                padded_rider_features
            ))

            # Process rider names
            riders = group['rider_name'].tolist()
            padded_riders = (riders + ['PAD'] * (max_riders - n_riders)) if n_riders < max_riders else riders[:max_riders]

            races_test.append(feature_matrix)
            rider_names_test.append(padded_riders)

        except Exception as e:
            print(f"Error processing race {race_name} {year}: {e}")
            continue

    X_test = np.array(races_test)
    rider_names_test = np.array(rider_names_test, dtype=object)

    np.save('/home/bsc/MLOps_diploma_app/mlops/X_test.npy', X_test)
    np.save('/home/bsc/MLOps_diploma_app/mlops/rider_names_test.npy', rider_names_test)
    
    return "Data preprocessing completed and saved."