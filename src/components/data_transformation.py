import sys
import numpy as np
import pandas as pd
from imblearn.combine import SMOTEENN
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.compose import ColumnTransformer

from src.constants import TARGET_COLUMN, SCHEMA_FILE_PATH, CURRENT_YEAR
from src.entity.config_entity import DataTransformationConfig
from src.entity.artifact_entity import DataTransformationArtifact, DataIngestionArtifact, DataValidatioArtifact
from src.exception import MyException
from src.logger import logging
from src.utils.main_utils import save_object, save_numpy_array_data, read_yaml_file


class DataTransformation:
    def __init__(self,data_ingestion_artifact:DataIngestionArtifact,
                 data_transformation_config:DataTransformationConfig,
            data_validation_artifact: DataValidatioArtifact):
        try:
            self.data_ingestion_artifact=data_ingestion_artifact
            self.data_transformation_config = data_transformation_config
            self.data_validation_artifact = data_validation_artifact 
            self._schema_config  = read_yaml_file(file_path=SCHEMA_FILE_PATH)
        except Exception as e:
            raise MyException(e,sys) 
    @staticmethod
    def read_data(file_path):
        try:
            return pd.read_csv(file_path)
        except Exception as e:
            raise MyException(e,sys)
        
    def get_data_transformer_object(self):
        logging.info('Entered data transformation object...')
        try:
            numeric_transformer = StandardScaler()
            min_max_scaler = MinMaxScaler()
            logging.info('transformer initiated')
            
            num_features = self._schema_config['num_features']
            mm_features = self._schema_config['mm_columns']
            logging.info('cols loaded from schema...')
            
            preprocessor = ColumnTransformer(
                transformers=[
                    ('StandardScaler',numeric_transformer,num_features),
                    ('MinMaxScaler',min_max_scaler,mm_features)
                ],remainder= 'passthrough'
            )
            final_pipeline = Pipeline(steps=[('Preprocessor',preprocessor)])
            logging.info('Final pipeline ready')
            logging.info('exited from get transformed..')
            return final_pipeline
        except Exception as e:
            raise MyException(e,sys) from e
    
    def _map_gender_column(self,df):
        logging.info('Mapping Gender column..')
        df['Gender'] = df['Gender'].map({'Female':0,'Male':1}).astype(int)
        return df
    
    def _create_dummy_columns(self,df):
        logging.info('creating dummy columns...')
        df = pd.get_dummies(df,drop_first=True)
        return df
    
    def _rename_columns(self, df):
        """Rename specific columns and ensure integer types for dummy columns."""
        logging.info("Renaming specific columns and casting to int")
        df = df.rename(columns={
            "Vehicle_Age_< 1 Year": "Vehicle_Age_lt_1_Year",
            "Vehicle_Age_> 2 Years": "Vehicle_Age_gt_2_Years"
        })
        for col in ["Vehicle_Age_lt_1_Year", "Vehicle_Age_gt_2_Years", "Vehicle_Damage_Yes"]:
            if col in df.columns:
                df[col] = df[col].astype('int')
        return df
    
    def _drop_id_column(self,df):
        logging.info('Dropping id columns....')
        drop_col = self._schema_config['drop_columns']
        if drop_col in df.columns:
            df = df.drop(drop_col,axis=1)
        return df
    
    def initiate_data_transformation(self):
        try:
            logging.info('Data transformation started....')
            if not self.data_validation_artifact.validation_status:
                raise Exception(self.data_validation_artifact.message)

            train_df = self.read_data(self.data_ingestion_artifact.trained_file_path)
            test_df = self.read_data(self.data_ingestion_artifact.test_file_path)
            logging.info('train and test data ready')
            
            # Target Column Separation
            input_feature_train_df = train_df.drop(columns=[TARGET_COLUMN], axis=1)
            target_feature_train_df = train_df[TARGET_COLUMN]
            
            input_feature_test_df = test_df.drop(columns=[TARGET_COLUMN], axis=1)
            target_feature_test_df = test_df[TARGET_COLUMN]            
            logging.info('input target column defined...')
            
            # Apply custom transformations
            input_feature_train_df = self._map_gender_column(input_feature_train_df)
            input_feature_train_df = self._drop_id_column(input_feature_train_df)
            input_feature_train_df = self._create_dummy_columns(input_feature_train_df)
            input_feature_train_df = self._rename_columns(input_feature_train_df)

            input_feature_test_df = self._map_gender_column(input_feature_test_df)
            input_feature_test_df = self._drop_id_column(input_feature_test_df)
            input_feature_test_df = self._create_dummy_columns(input_feature_test_df)
            input_feature_test_df = self._rename_columns(input_feature_test_df)

            
            logging.info("Starting data transformation")
            preprocessor = self.get_data_transformer_object()
            
            input_feature_train_arr = preprocessor.fit_transform(input_feature_train_df)
            input_feature_test_arr = preprocessor.transform(input_feature_test_df)
            logging.info('Preprocessor transformation done...')
            
            smt = SMOTEENN(sampling_strategy='minority')
            input_feature_train_final, target_feature_train_final = smt.fit_resample(
                input_feature_train_arr, target_feature_train_df
            )
            logging.info('Applied SMOTEENN to training set only.')
            
            input_feature_test_final = input_feature_test_arr
            target_feature_test_final = target_feature_test_df
            
            train_arr = np.c_[input_feature_train_final, np.array(target_feature_train_final)]
            test_arr = np.c_[input_feature_test_final, np.array(target_feature_test_final)]
            logging.info('Concatenation done for train_arr and test_arr...')
            
            # Saving artifacts
            save_object(self.data_transformation_config.transformed_object_file_path, preprocessor)
            save_numpy_array_data(self.data_transformation_config.transformed_train_file_path, array=train_arr)
            save_numpy_array_data(self.data_transformation_config.transformed_test_file_path, array=test_arr)
            
            return DataTransformationArtifact(
                transformed_object_file_path=self.data_transformation_config.transformed_object_file_path,
                transformed_train_file_path=self.data_transformation_config.transformed_train_file_path,
                transformed_test_file_path=self.data_transformation_config.transformed_test_file_path
            )

        except Exception as e:
            raise MyException(e, sys) from e