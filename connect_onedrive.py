import json
import logging
import os
import sqlite3
import time

import msal
import requests


class OneDriveConnector:
    def __init__(self, client_id, client_secret, authority, scopes, endpoint, mail, drive_name):
        """
        Initialize OneDriveConnector object.
        :param client_id:       Application (client) ID
        :param authority:       https://login.microsoftonline.com/{tenant_id}
        :param scopes:          https://graph.microsoft.com/.default
        :param endpoint:        https://graph.microsoft.com/v1.0
        :param mail:            your mail address
        :param drive_name:      Location of the folder where the database is stored, default sqlite
        """
        self.path_name = None
        self.path_id = None
        self.token = None
        self.app = None
        self.user_id = None
        self.drive_id = None
        self.client_id = client_id
        self.client_secret = client_secret
        self.authority = authority
        self.scopes = scopes
        self.endpoint = endpoint
        self.mail = mail
        self.drive_name = drive_name
        self.local = None

    def init_app(self) -> bool:
        """
        Initialize app with MSAL library.
        :return: True if connection to OneDrive is successful, False otherwise.
        """

        self.local = sqlite3.connect('local.db')
        cursor = self.local.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS onedrive_info 
        (_id INTEGER PRIMARY KEY AUTOINCREMENT,
         id TEXT,
         name TEXT
        )""")
        self.local.commit()

        is_connected = self.connect()
        if not is_connected:
            for i in range(5):
                logging.warning(f"Trying to connect to OneDrive for the {i + 1} time...")
                is_connected = self.connect()
                if is_connected:
                    break
            if not is_connected:
                logging.error("Failed to connect to OneDrive")
                return False

        is_token = self.get_token()
        if not is_token:
            for i in range(5):
                logging.warning(f"Trying to get token for OneDrive for the {i + 1} time...")
                is_token = self.get_token()
                if is_token:
                    break

            if not is_token:
                return False

        is_user = self.get_user_id()
        if not is_user:
            return False

        is_drive = self.get_drive_id()
        if not is_drive:
            print("Failed to get drive id for OneDrive")
            return False

        return True

    def connect(self) -> bool:
        """
        Connect to OneDrive using MSAL library.
        :return: True if connection is successful, False otherwise.
        """
        try:
            self.app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=self.authority,
                client_credential=self.client_secret,
            )
            return True
        except Exception as e:
            logging.error(f"Failed to connect to OneDrive: {e}")
            return False

    def get_token(self) -> bool:
        """
        Get access token for OneDrive.
        :return: True if token is found, False otherwise.
        """
        try:
            result = self.app.acquire_token_for_client(scopes=self.scopes)
            if not result.get("access_token"):
                logging.warning("No suitable token exists in cache. Let's get a new one from AAD.")
                result = self.app.acquire_token_for_client(scopes=self.scopes)
            self.token = result.get("access_token")
            print(f"\033[1;32mAccess token: {self.token}\033[0m")
            return True
        except Exception as e:
            logging.error(f"Failed to get token: {e}")
            return False

    def get_user_id(self) -> bool:
        """
        Get user id of the connected user.
        :return: True if user id is found, False otherwise.
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
        }
        response = requests.get(
            f'{self.endpoint}/users/', headers=headers
        )
        data = json.loads(response.content.decode("utf-8"))
        try:
            self.user_id = None
            for v in data['value']:
                if v['mail'] == self.mail:
                    self.user_id = v['id']
                    break

            if not self.user_id:
                logging.error(f"User with email {self.mail} not found in OneDrive")
                return False

            print(f"\033[1;32mUser id: {self.user_id}\033[0m")
            return True
        except Exception as e:
            logging.error(f"Failed to get user id from get_user_id.response.content: {e}")

    def get_drive_id(self) -> bool:
        """
        Get drive id of the connected user.
        :return: True if drive id is found, False otherwise.
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
        }
        response = requests.get(
            f"{self.endpoint}/users/{self.user_id}/drives", headers=headers
        )
        data = json.loads(response.content.decode("utf-8"))
        self.drive_id = None
        try:
            for drive in data['value']:
                try:
                    self.drive_id = drive['id']
                    self.drive_name = drive['name']
                    print(f"\033[1;32mDrive id: {self.drive_id}\033[0m")
                    return True
                except Exception as e:
                    logging.error(f"Failed to get drive id from get_drive_id.response.content.value: {e}")
                    return False
        except Exception as e:
            logging.error(f"Failed to get value from get_drive_id.response.content: {e}")
            return False

    def get_path_id(self, dir_name: str) -> bool:
        """
        :param dir_name: Location of the folder where the database is stored, default sqlite
        :return:
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
        }
        response = requests.get(f"{self.endpoint}/drives/{self.drive_id}/root/children",
                                headers=headers)
        data = json.loads(response.content.decode("utf-8"))
        # Find the file with the given name
        try:
            for v in data['value']:
                if v['name'] == dir_name:
                    self.path_id = v['id']
                    self.path_name = v['name']
                    print(f"\033[1;32mPath id: {self.path_id}, Path name: {self.path_name}\033[0m")
                    break

            if self.path_id is None:
                requests.post(f"{self.endpoint}/users/{self.user_id}/drives/{self.drive_id}/root/children",
                              headers=headers,
                              json={"name": dir_name, "folder": {}})
                logging.warning(f'{dir_name} is undefined in OneDrive(id: {self.drive_id}), creating a new folder')
                return False
            else:
                return True
        except Exception as e:
            logging.error(f'Failed to get value from check_path.response.content: {e}')
            return False

    def update_local_info(self) -> bool:
        """
        Update file information in onedrive into local database
        :return:
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
        }
        response = requests.get(f"{self.endpoint}/drives/{self.drive_id}/items/{self.path_id}/children",
                                headers=headers)
        try:
            drive_items = json.loads(response.content.decode("utf-8"))['value']
            cursor = self.local.cursor()
            for item in drive_items:
                try:
                    file_id = item['id']
                    file_name = item['name']
                    cursor.execute("""SELECT * FROM onedrive_info WHERE name=?""", (file_name,))
                    is_find = cursor.fetchone()
                    if is_find:
                        cursor.execute("""UPDATE onedrive_info SET id=? WHERE name=?""",
                                       (file_id, file_name,))
                    else:
                        cursor.execute("""INSERT INTO onedrive_info (id, name) VALUES (?,?)""", (file_id, file_name,))

                    self.local.commit()

                except Exception as e:
                    logging.error(f"Failed to get file id and name from update_local_info.response.content.value: {e}")
                    return False

            params = ','.join('?' for _ in drive_items)
            cursor.execute("""DELETE FROM onedrive_info WHERE  name NOT IN ({0})""".format(params),
                           [item['name'] for item in drive_items])

            print(f"\033[1;34mUpdate local database successfully\033[0m")
            self.local.commit()
            return True

        except Exception as e:
            logging.error(f"Failed to get file information from update_local_info.response.content: {e}")
            return False

    def create_local_db(self, file_name: str, table_name: str, data: dict):
        """
        :param data:
        :param table_name:
        :param file_name:
        :return:
        """
        columns = ', '.join([f'{k} {v}' for k, v in data.items()])

        is_find = self.find_db(file_name)
        if not is_find:
            onedrive_db = sqlite3.connect(file_name)
            curr = onedrive_db.cursor()
            curr.execute(f"""CREATE TABLE IF NOT EXISTS {table_name} 
            (_id INTEGER PRIMARY KEY AUTOINCREMENT,
            {columns}
            )""")
            onedrive_db.commit()
            onedrive_db.close()
            self.post_file(file_name, file_name)
            self.update_local_info()

        print(f"\033[1;32m  \033[0m")
        onedrive_db = sqlite3.connect(file_name)
        curr = onedrive_db.cursor()
        try:  # create table if not exist
            curr.execute(f"""CREATE TABLE IF NOT EXISTS {table_name} (
                _id INTEGER PRIMARY KEY AUTOINCREMENT,
                {columns})""")
            onedrive_db.commit()
            onedrive_db.close()
            return True
        except Exception as e:
            logging.error(f"Failed to create local database: {e}")
            return False

    def find_db(self, file_name: str) -> bool:
        """
        :param file_name:
        :return:
        """

        self.update_local_info()
        cursor = self.local.cursor()
        cursor.execute("""SELECT * FROM onedrive_info WHERE name=?""", (file_name,))
        in_onedrive = cursor.fetchone()
        in_local = os.path.exists(file_name)
        if in_local:
            if not in_onedrive:
                self.post_file(file_name, file_name)
                self.update_local_info()
        elif in_onedrive:
            self.download_file(in_onedrive[0])
        else:
            return False
        return True

    def post_file(self, file_path: str, file_name: str, behavior: str = 'fail', ) -> bool:
        """
        Upload file to OneDrive.
        :param file_path:
        :param file_name:
        :param behavior: 'fail' 'replace' 'rename'
        :return:
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            'Content-Type': 'application/json'
        }
        data = {
            'item': {
                '@microsoft.graph.conflictBehavior': behavior,
            }
        }

        response = requests.post(
            f"{self.endpoint}/drives/{self.drive_id}/items/{self.path_id}:/{file_name}:/createUploadSession",
            headers=headers, json=data)
        if response.status_code == 200:
            chunk_size = 10485760
            upload_url = response.json()['uploadUrl']
            print(f"\033[1;33mUpload url: {upload_url}\033[0m")
            with open(file_path, 'rb') as f:
                # Slice Upload
                file_size = os.path.getsize(file_path)
                start = 0
                end = chunk_size - 1 if chunk_size - 1 < file_size else file_size - 1

                while start < file_size:
                    data_len = end - start + 1
                    headers = {
                        'Content-Length': str(data_len),
                        'Content-Range': f'bytes {start}-{end}/{file_size}'
                    }
                    response = requests.put(upload_url, headers=headers, data=f.read(data_len))
                    if response.status_code == 202:
                        start = int(response.json()['nextExpectedRanges'][0].split('-')[1]) + 1
                        end = start + chunk_size - 1 if start + chunk_size - 1 < file_size else file_size - 1
                    elif response.status_code == 201:
                        print(f"\033[1;33mUpload successfully {file_name}\033[0m")
                        return True
                    elif response.status_code / 100 == 5:
                        time.sleep(2)
                    elif response.status_code == 200:
                        return True
                    else:
                        logging.error(f"Failed to upload {file_name} to OneDrive: {response.status_code}")
                        return False
        else:
            logging.error(f"Failed to get uploadUrl from post_file.response.content: {response.status_code}")
            return False

    def download_file(self, file_id: str) -> bool:
        """
        Download file from OneDrive.
        :param file_id:
        :return:
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
        }
        response = requests.get(
            f"{self.endpoint}/drives/{self.drive_id}/items/{file_id}/content", headers=headers
        )

        if response.status_code == 200:
            file_name = response.headers['Content-Disposition'].split('filename=')[1].strip('"')
            with open(file_name, 'wb') as f:
                f.write(response.content)
            print(f"\033[1;33mDownload successfully {file_name}\033[0m")
            return True
        else:
            logging.error(f"Failed to download {file_id} from OneDrive: {response.status_code}")
            return False

    def operate_db(self, file_name: str, table_name: str, *args):
        """
        Operate database in OneDrive.
        :param args:
        ('insert', {'name': 'Alice', 'age': 20})
        ('update', {'age': 21}, {'_id':1})
        ('delete', {'id':1})
        ('select')     # return all rows
        ('select', {'name': 'Alice'})  # return rows with name 'Alice'
        :param file_name:
        :param table_name:
        :param file_name:
        :return:
        """

        onedrive_db = sqlite3.connect(file_name)
        curr = onedrive_db.cursor()

        match args[0]:
            case 'insert':
                data = args[1]
                curr.execute(
                    f"""INSERT INTO {table_name} ({', '.join(data.keys())}) VALUES 
                        ({', '.join(['?' for _ in data.values()])})""", tuple(data.values()))
            case 'update':
                set_clause = ', '.join(f"{key} = :{key}" for key in args[1])
                where_clause = ' AND '.join(f"{key} = :where_{key}" for key in args[2])
                params = {**args[1], **{'where_' + k: v for k, v in args[2].items()}}
                curr.execute(f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}", params)
            case 'delete':
                where, value = next(iter(args[1].items()))
                curr.execute(f"""DELETE FROM {table_name} WHERE {where}=?""", (value,))
            case 'select':  # TODO syndicated search
                try:
                    where, value = next(iter(args[1].items()))
                    curr.execute(f"""SELECT * FROM {table_name} WHERE {where}=?""", (value,))
                except Exception:
                    curr.execute(f"""SELECT * FROM {table_name}""")

                rows = curr.fetchall()
                onedrive_db.commit()
                onedrive_db.close()
                return rows
            case _:
                logging.error(f"Failed to operate_db: {args[0]} is not a valid operation")

        onedrive_db.commit()
        onedrive_db.close()
        self.post_file(file_name, file_name, 'replace')
