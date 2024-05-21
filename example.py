import logging

from config import config
from connect_onedrive import OneDriveConnector

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
    connector = OneDriveConnector(config['client_id'], config['secret'], config['authority'], config['scopes'],
                                  config['endpoint'], config['mail'], config['drive_name'])

    connector.init_app()
    is_path_exist = connector.get_path_id(config['drive_name'])
    if not is_path_exist:
        for i in range(1, 4):
            logging.warning(f"Creating directory {config['drive_name']} {i}/3")
            is_path_exist = connector.get_path_id(config['drive_name'])
            if is_path_exist:
                break
    else:
        print(f"\033[1;32mDirectory {config['drive_name']} already exists\033[0m")

    connector.create_local_db('20240521.db', 'test', {'name': 'TEXT', 'num': 'INTEGER', 'test': 'TEXT'})

    rows = connector.operate_db('20240521.db', 'test', 'select',{'_id':2})
    for row in rows:
        print(row)
    print('-------')
