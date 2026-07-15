import json
import sys
import os

import pandas as pd

from pandas import DataFrame

from src.exception import MyException
from src.logger import logging
from src.utils.main_utils import read_yaml_file
from src.entity.artifact_entity import DataIngestionArtifact, DataValidatioArtifact
from src.entity.config_entity import DataValidationConfig
from src.constants import SCHEMA_FILE_PATH

class DataValidation():
    def __init__(self,data_ingestion_artifact:DataIngestionArtifact,data_validation_config:DataValidationConfig):
        self.data_ingestion_artifact = data_ingestion_artifact
        self.data_validation_config = data_validation_config
        self._schema_config = read_yaml_file(file_path = SCHEMA_FILE_PATH)
    
    def validate_number_of_columns(self,dataframe:DataFrame):
        try:
            status = len(dataframe.columns) == len(self._schema_config['columns'])
            logging.info(f'Is requred column present {status}')
            return status
        except Exception as e:
            raise MyException(e,sys) from e
        
    def is_column_exist(self,df:DataFrame):
        try:
            df_col = df.columns
            missing_numeric_col = []
            missing_cat_col = []
            for col in self._schema_config['numerical_columns']:
                if col not in df_col:
                    missing_numeric_col.append(col)

            if len(missing_numeric_col)>0:
                logging.info(f'Missing numeric columns are {missing_numeric_col}')
            
            for col in self._schema_config['categorical_columns']:
                if col not in df_col:
                    missing_cat_col.append(col)
                    
            if len(missing_cat_col)>0:
                logging.info(f'Missing categorical columns are {missing_cat_col}')   
                
        except Exception as e:
            raise MyException(e,sys) from e
                
    @staticmethod
    def read_data(file_path):
        try:
            return pd.read_csv(file_path)
        except Exception as e:
            raise MyException(e,sys) from e
    
    def initiate_data_validation(self):
        try:
            validation_error_mesage  = ""
            logging.info("starting data Validation..")
            train_df,test_df = (DataValidation.read_data(file_path=self.data_ingestion_artifact.trained_file_path),
                                DataValidation.read_data(file_path=self.data_ingestion_artifact.test_file_path))   
        
            status = self.validate_number_of_columns(dataframe=train_df)
            if not status:
                validation_error_mesage += f'columns are missing in train_df'
            else:
                logging.info(f'All requred column are present in train_df is {status}')
            
            status = self.validate_number_of_columns(dataframe=test_df)
            if not status:
                validation_error_mesage += f'columns are missing in test_df'
            else:
                logging.info(f'All requred column are present in test_df is {status}')
            
            validation_status = len(validation_error_mesage)== 0

            data_validation_artiact = DataValidatioArtifact(
                validation_status=validation_status,
                message= validation_error_mesage,
                validation_report_file_path = self.data_validation_config.validation_report_file_path)
            
            #path
            report_dir = os.path.dirname(self.data_validation_config.validation_report_file_path)
            os.makedirs(report_dir,exist_ok = True)
            
            validation_report = {
                "validation_status": validation_status,
                "message": validation_error_mesage
            }
            with open (self.data_validation_config.validation_report_file_path,'w') as file:
                json.dump(validation_report,file,indent=4)
                
            logging.info('Data validaton report has been creadted and saved to json file.')
            logging.info(f'Data validation artifact {data_validation_artiact}')
            return data_validation_artiact
        except Exception as e:
            raise MyException(e,sys) from e