tenant_id = 'your_tenant_id'
client_id = 'your_client_id'
mail = 'your_email'

config = {
    'mail': mail,
    'drive_name': 'sqlite',
    'client_id': client_id,
    'authority': f'https://login.microsoftonline.com/{tenant_id}',
    'secret': 'your_secret',
    'scopes': ['https://graph.microsoft.com/.default'],
    'endpoint': 'https://graph.microsoft.com/v1.0'
}
