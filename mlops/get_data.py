import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, OrdinalEncoder

merged_data = pd.read_csv('/Users/feliks/Documents/Faks/Diplomska/App/common/final_data.csv')

def pad_riders(rider_list, max_riders, pad_value='Unknown'):
        if len(rider_list) < max_riders:
            return rider_list + [pad_value] * (max_riders - len(rider_list))
        else:
            return rider_list[:max_riders]
        
def split_test_train_data(index):
    # Split data into training and testing sets based on 'year'
    train_data = merged_data[merged_data['year'] < 2024]
    test_data = merged_data[merged_data['year'] == 2024]

    # Add data from test set to training set incrementally
    unique_race_names = test_data['name'].unique()
    races_to_move = unique_race_names[:index+1]

    race_data_to_move = test_data[test_data['name'].isin(races_to_move)]
    train_data = pd.concat([train_data, race_data_to_move], ignore_index=True)
    test_data = test_data[~test_data['name'].isin(races_to_move)].reset_index(drop=True)

    return train_data, test_data

def preprocess_data(index):
    # Define feature groups
    race_numerical = [
        'distance', 'vertical_meters', 'speed', 'year', 'score', 'quality', 'ranking'
    ]
    race_categorical = ['name']
    rider_numerical = [
        'weight', 'height', 'one_day', 'gc', 'tt', 'sprint',
        'climber', 'hills', 'age'
    ]
    rider_categorical_low = ['speciality']
    rider_categorical_high = ['nationality', 'team', 'rider_name']

    train_data, test_data = split_test_train_data(index)

    # Determine the maximum number of riders across all races in both training and testing data
    max_riders_train = train_data.groupby(['name', 'year']).size().max()
    max_riders_test = test_data.groupby(['name', 'year']).size().max()
    max_riders = max(max_riders_train, max_riders_test)

    # Create preprocessing pipelines
    race_numeric_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', MinMaxScaler())
    ], memory=None)

    race_categorical_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='constant', fill_value='Unknown')),
        ('onehot', OneHotEncoder(
            drop='first', sparse_output=False, handle_unknown='ignore'
        ))
    ], memory=None)

    rider_numeric_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', MinMaxScaler())
    ], memory=None)

    rider_categorical_low_pipeline = Pipeline([
        ('imputer', SimpleImputer(
            strategy='constant', fill_value='Unknown')),
        ('onehot', OneHotEncoder(
            drop='first', sparse_output=False, handle_unknown='ignore'
        ))
    ], memory=None)

    rider_categorical_high_pipeline = Pipeline([
        ('imputer', SimpleImputer(
            strategy='constant', fill_value='Unknown')),
        ('ordinal', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1))
    ], memory=None)

    # Fit pipelines on training data
    race_numeric_pipeline.fit(train_data[race_numerical])
    race_categorical_pipeline.fit(train_data[race_categorical])
    rider_numeric_pipeline.fit(train_data[rider_numerical])
    rider_categorical_low_pipeline.fit(train_data[rider_categorical_low])
    rider_categorical_high_pipeline.fit(train_data[rider_categorical_high])

    # Initialize lists for training data
    races_train = []
    targets_train = []
    rider_names_train = []

    for (race_name, year), group in train_data.groupby(['name', 'year']):
        try:
            # Extract race-level features
            race_num_data = group[race_numerical].iloc[[0]]
            race_cat_data = group[race_categorical].iloc[[0]]

            # Extract rider-level features
            rider_num_data = group[rider_numerical]
            rider_cat_data_low = group[rider_categorical_low]
            rider_cat_data_high = group[rider_categorical_high]

            # Transform features using fitted pipelines
            race_num_processed = race_numeric_pipeline.transform(race_num_data)
            race_cat_processed = race_categorical_pipeline.transform(race_cat_data)
            rider_num_processed = rider_numeric_pipeline.transform(rider_num_data)
            rider_cat_low_processed = rider_categorical_low_pipeline.transform(rider_cat_data_low)
            rider_cat_high_processed = rider_categorical_high_pipeline.transform(rider_cat_data_high)

            # Combine features
            race_features = np.hstack((race_num_processed, race_cat_processed))
            rider_features = np.hstack((rider_num_processed, rider_cat_low_processed, rider_cat_high_processed))

            # Pad or truncate rider_features to max_riders
            n_riders = rider_features.shape[0]
            if n_riders < max_riders:
                pad_width = max_riders - n_riders
                padded_rider_features = np.pad(
                    rider_features,
                    ((0, pad_width), (0, 0)),
                    mode='constant',
                    constant_values=0
                )
            else:
                padded_rider_features = rider_features[:max_riders, :]

            # Create feature matrix by repeating race_features and concatenating with rider_features
            feature_matrix = np.hstack((
                np.tile(race_features, (max_riders, 1)),
                padded_rider_features
            ))

            # Calculate probabilities for first 3 riders and pad or truncate to max_riders
            ranks = group['rank'].values
            padded_probabilities = np.zeros(max_riders)
            probabilities = np.array([np.exp(-ranks[:3]) / np.sum(np.exp(-ranks[:3]))])
            padded_probabilities[0:3] = probabilities

            # Collect rider names and pad or truncate to max_riders
            riders = group['rider_name'].tolist()
            if n_riders < max_riders:
                padded_riders = riders + ['PAD'] * (max_riders - n_riders)
            else:
                padded_riders = riders[:max_riders]

            # Append data to lists
            races_train.append(feature_matrix)
            targets_train.append(padded_probabilities)
            rider_names_train.append(padded_riders)

        except Exception as e:
            print(f"Error processing race {race_name} {year}: {e}")
            continue

    # Initialize lists for test data
    races_test = []
    targets_test = []
    rider_names_test = []

    for (race_name, year), group in test_data.groupby(['name', 'year']):
        try:
            # Extract race-level features
            race_num_data = group[race_numerical].iloc[[0]]
            race_cat_data = group[race_categorical].iloc[[0]]

            # Extract rider-level features
            rider_num_data = group[rider_numerical]
            rider_cat_data_low = group[rider_categorical_low]
            rider_cat_data_high = group[rider_categorical_high]

            # Transform features using pipelines fitted on training data
            race_num_processed = race_numeric_pipeline.transform(race_num_data)
            race_cat_processed = race_categorical_pipeline.transform(race_cat_data)
            rider_num_processed = rider_numeric_pipeline.transform(rider_num_data)
            rider_cat_low_processed = rider_categorical_low_pipeline.transform(rider_cat_data_low)
            rider_cat_high_processed = rider_categorical_high_pipeline.transform(rider_cat_data_high)

            # Combine features
            race_features = np.hstack((race_num_processed, race_cat_processed))
            rider_features = np.hstack((rider_num_processed, rider_cat_low_processed, rider_cat_high_processed))

            # Pad or truncate rider_features to max_riders
            n_riders = rider_features.shape[0]
            if n_riders < max_riders:
                pad_width = max_riders - n_riders
                padded_rider_features = np.pad(
                    rider_features,
                    ((0, pad_width), (0, 0)),
                    mode='constant',
                    constant_values=0
                )
            else:
                padded_rider_features = rider_features[:max_riders, :]

            # Create feature matrix by repeating race_features and concatenating with rider_features
            feature_matrix = np.hstack((
                np.tile(race_features, (max_riders, 1)),
                padded_rider_features
            ))

            # Calculate probabilities for first 3 riders and pad or truncate to max_riders
            ranks = group['rank'].values
            padded_probabilities = np.zeros(max_riders)
            probabilities = np.array([np.exp(-ranks[:3]) / np.sum(np.exp(-ranks[:3]))])
            padded_probabilities[0:3] = probabilities

            # Collect rider names and pad or truncate to max_riders
            riders = group['rider_name'].tolist()
            if n_riders < max_riders:
                padded_riders = riders + ['PAD'] * (max_riders - n_riders)
            else:
                padded_riders = riders[:max_riders]

            # Append data to lists
            races_test.append(feature_matrix)
            targets_test.append(padded_probabilities)
            rider_names_test.append(padded_riders)

        except Exception as e:
            print(f"Error processing race {race_name} {year}: {e}")
            continue
    # Find maximum number of riders across all data
    max_riders = max(
        max(len(riders) for riders in rider_names_train),
        max(len(riders) for riders in rider_names_test)
    )

    # Convert lists to NumPy arrays
    X_train = np.array(races_train)
    y_train = np.array(targets_train)
    rider_names_train = np.array(rider_names_train, dtype=object)

    X_test = np.array(races_test)
    y_test = np.array(targets_test)
    rider_names_test = np.array(rider_names_test, dtype=object)

    # Save the data
    np.save('/Users/feliks/Documents/Faks/Diplomska/App/mlops/X_train.npy', X_train)
    np.save('/Users/feliks/Documents/Faks/Diplomska/App/mlops/y_train.npy', y_train)
    np.save('/Users/feliks/Documents/Faks/Diplomska/App/mlops/rider_names_train.npy', rider_names_train)

    np.save('/Users/feliks/Documents/Faks/Diplomska/App/mlops/X_test.npy', X_test)
    np.save('/Users/feliks/Documents/Faks/Diplomska/App/mlops/y_test.npy', y_test)
    np.save('/Users/feliks/Documents/Faks/Diplomska/App/mlops/rider_names_test.npy', rider_names_test)

    print("Data preprocessing completed and saved.")