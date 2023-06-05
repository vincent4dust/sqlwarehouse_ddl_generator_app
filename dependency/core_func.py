import os
import pandas as pd
from datetime import datetime
import configparser
import logging

def get_parameter_config(parameter_config_path):
    """
    Read the parameter config file
    :param src parameter_config_path: parameter file path
    :return: config
    :rtype config: dict
    """
    config_parser = configparser.ConfigParser()
    config_parser.read(parameter_config_path)
    config = {}
    config["DEFAULT"] = {}

    if len(config_parser.sections()) != 0:
        for sec in config_parser.sections():
            config[sec] = {}
    
    for sec in config:
        for key in config_parser[sec]:
            config[sec][key.upper()] = config_parser[sec][key]

    return config

def get_table_list(table_list_path):
    """
    Get the table list to generate sql
    :param table_list_path: table list file path
    :return: table_list
    :rtype table_list: list
    """
    table_list = []
    if os.path.exists(table_list_path):
        with open(table_list_path, "r") as in_file:
            for line in in_file:
                table_list.append(line.rstrip().upper())
    else:
        logging.error(f"The table list file not exists, '{table_list_path}'")
        raise UserWarning(f"The table list file not exists, '{table_list_path}'")
    
    return table_list

def read_input_file(source_file_path):
    """
    Read the input csv file
    :param str source_file: file name with csv extension
    :param str source_folder: input folder
    :return: src_data
    :rtype src_data: dataframe
    """
    if os.path.exists(source_file_path):
        if source_file_path.endswith(".csv"):
            src_data = pd.read_csv(source_file_path)
            src_data.columns = map(str.upper, src_data.columns)
    else:
        logging.error(f"The source file not exists, '{source_file_path}'")
        raise UserWarning(f"The source file not exists, '{source_file_path}'")

    return src_data

def get_sql(src_data, table_list, ad_group_list):
    """
    To generate the sql
    :param str src_data: read in data
    :param list table_list: table list to generate the sql
    :param dict ad_group_list: the list of ad group of different domain
    :return: sql_stmt
    :rtype sql_stmt: str
    """
    src_col = src_data.columns
    if "DB_NAME" in src_col:
        src_data["DB_NAME"] = src_data["DB_NAME"].apply(lambda x: x.upper())
    else:
        raise UserWarning("No column 'DB_NAME' found in source file")

    if "TBL_NAME" in src_col:
        src_data["TBL_NAME"] = src_data["TBL_NAME"].apply(lambda x: x.upper())
    else:
        raise UserWarning("No column 'TBL_NAME' found in source file")

    if "COL_NAME" in src_col:
        src_data["COL_NAME"] = src_data["COL_NAME"].apply(lambda x: x.upper())
    else:
        raise UserWarning("No column 'COL_NAME' found in source file")
    
    sql_stmt = ""
    for table_name in table_list:
        try:
            temp_df = src_data[src_data["TBL_NAME"] == table_name]

            db_name_list = temp_df["DB_NAME"].unique()
            # make sure the same table name has same schema name
            num_of_schema = len(db_name_list)
            if num_of_schema == 1:
                db_schema_name = db_name_list[0]
            elif num_of_schema > 1:
                raise UserWarning(f"'DB_NAME' is not unique for table '{table_name}'")
            else:
                raise UserWarning(f"Table name is not found, '{table_name}'")

            # view schema name concat from database schema name
            view_schema_name = db_schema_name[:-6]

            col_list = temp_df["COL_NAME"].tolist()
            col_sql_stmt = ""
            for col_name in col_list:
                # determine the PII column name
                conf_value = temp_df[temp_df["COL_NAME"] == col_name]["DATA CLASSIFICATION"].values.astype(str)[0]
                if conf_value == "Highly Confidential":
                    # determine the ad group of respective domain
                    domain_value = temp_df[temp_df["COL_NAME"] == col_name]["DATA DOMAIN"].values.astype(str)[0]
                    if domain_value.upper() in ad_group_list:
                        ad_group = ad_group_list[domain_value.upper()]
                    else:
                        raise UserWarning(f"'{domain_value}' not found in data domain list")
                    col_sql_stmt += f"CASE\n\tWHEN IS_MEMBER('{ad_group}') THEN {col_name}\n\tELSE 'NO ACCESS'\nEND AS {col_name},\n"
                else:
                    col_sql_stmt += f"{col_name},\n"

            # get history
            his_table_name = table_name + "_HIS"
            col_his_sql_stmt = col_sql_stmt
            his_col_list = ["IS_ACTIVE", "EFF_ST_DT", "EFF_END_DT"]
            for his_col in his_col_list:
                col_his_sql_stmt += f"{his_col},\n"

            col_sql_stmt = col_sql_stmt.rstrip()
            col_sql_stmt = col_sql_stmt[:-1]
            col_his_sql_stmt = col_his_sql_stmt.rstrip()
            col_his_sql_stmt = col_his_sql_stmt[:-1]

            create_sql_stmt = f"CREATE OR REPLACE VIEW {view_schema_name}.{table_name}\nAS\nSELECT\n{col_sql_stmt}\nFROM\n{db_schema_name}.{table_name};"
            owner_sql_stmt = f"ALTER VIEW {view_schema_name}.{table_name} OWNER TO hive_owner;"

            create_his_sql_stmt = f"CREATE OR REPLACE VIEW {view_schema_name}.{his_table_name}\nAS\nSELECT\n{col_his_sql_stmt}\nFROM\n{db_schema_name}.{his_table_name};"
            owner_his_sql_stmt = f"ALTER VIEW {view_schema_name}.{his_table_name} OWNER TO hive_owner;"

            sql_stmt += create_sql_stmt
            sql_stmt += "\n"
            sql_stmt += owner_sql_stmt
            sql_stmt += "\n\n"

            logging.info(f"Done for {table_name}")

            sql_stmt += create_his_sql_stmt
            sql_stmt += "\n"
            sql_stmt += owner_his_sql_stmt
            sql_stmt += "\n\n"

            logging.info(f"Done for {his_table_name}")

        except Exception as e:
            raise UserWarning(e)

    return sql_stmt

def write_to_output(curr_time, sql_stmt, output_folder):
    """
    Write a sql file
    :param str curr_time: current time to name output file
    :param str sql_stmt: content to write in the output file
    :param str output_folder: the output folder
    :return:
    """
    file_name = f"{curr_time}.sql"
    output_file_name = os.path.join(output_folder, file_name)
    try:
        with open(output_file_name, "w") as out_file:
            out_file.write(sql_stmt)

        logging.info(f"Output file path: {output_file_name}")
    except Exception as e:
        logging.error(e)
        raise UserWarning("Failed to write to output folder")

def main(source_file_path, output_folder, table_list_path, config):
    """
    Main function
    :return:
    """
    curr_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    logging.info(f"########################### {curr_time}.sql ###########################")

    table_list = get_table_list(table_list_path)

    logging.info(f"Source file path: {source_file_path}")

    env = config["DEFAULT"]["ENV"]
    ad_group_list = config[env]
    logging.info("Env: {}".format(env))

    src_data = read_input_file(source_file_path)
    sql_stmt = get_sql(src_data, table_list, ad_group_list)
    write_to_output(curr_time, sql_stmt, output_folder)

if __name__ == "__main__":
    source_file_path = None
    output_folder = None
    table_list_path = None
    config = None
    main(source_file_path, output_folder, table_list_path, config)