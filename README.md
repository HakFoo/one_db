# Introduction

A simple module to use onedrive as database storage.<br>
Only simple functionality has been implemented, and I'm not sure that it will work well
___

## Installation

<code>git clone https://github.com/HakFoo/one_db.git</code><br>
<code>pip install -r requirements.txt</code>

## Usage

1. Registering your application in Microsoft Entra admin center.
   &nbsp; [Microsoft Entra admin center](https://entra.microsoft.com/#home)
   ![](https://github.com/HakFoo/MarkdownImage/blob/master/one_db/home.jpg?raw=true)<br>
   ![](https://github.com/HakFoo/MarkdownImage/blob/master/one_db/register.jpg?raw=true)<br>
   Create secret.<br>
   ![](https://github.com/HakFoo/MarkdownImage/blob/master/one_db/secret.jpg?raw=true)<br>
   Don't forget to use the administrator to grant permissions<br>
   ![](https://github.com/HakFoo/MarkdownImage/blob/master/one_db/api.jpg?raw=true)<br>
   Get client ID and tenant ID<br>
   ![](https://github.com/HakFoo/MarkdownImage/blob/master/one_db/msg.jpg?raw=true)<br>
2. Copy the config.example.py to config.py and fill in the values.<br>
   drive_name is the name of the onedrive folder.Defaults to the sqlite folder in the root directory.<br>
3. Run the example.py.<br>

```python
from datetime import datetime

from onedrive_db import OneDriveDB

from config import config

db = OneDriveDB(config['client_id'], config['secret'], config['authority'], config['scopes'],
                config['endpoint'], config['mail'], config['drive_name'])
db.init_app()

# create loacl db
db_name = datetime.now().strftime('%Y-%m-%d')
db.create_local_db(db_name, 'label_name', {'name': 'TEXT', 'num': 'INTEGER', 'test': 'TEXT'})

# insert data
db.operate_db(db_name, 'label_name', 'insert', {'name': 'test1', 'num': 1, 'test': 'test1'})
# update data
db.operate_db(db_name, 'label_name', 'update', {'name': 'test1', 'num': 2, 'test': 'test2'}, {'name': 'test1'})
# delete data
db.operate_db(db_name, 'label_name', 'delete', {'_id': 1})
# select all data
rows = db.operate_db(db_name, 'label_name', 'select')
# select data by condition
rows = db.operate_db(db_name, 'label_name', 'select', {'name': 'test1'})
```