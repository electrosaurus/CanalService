import os.path
import logging
import google.auth.transport.requests
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import pandas as pd
import requests
from argparse import ArgumentParser
from xml.etree import ElementTree
import sqlalchemy
from datetime import datetime
from time import sleep
from telegram_notifier import TelegramNotifier

logger = logging.getLogger('main')

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

USD_CURRENCY_CODE = 'R01235'


def get_currency_exchange_rate(currency_code):
    ''' Get current exchange rate of a currency.
    
    Parameters
    ----------
    currency_code : str
        Currency ID (see https://www.cbr.ru/development/SXML/).
    '''
    resp = requests.get('https://www.cbr.ru/scripts/XML_daily.asp')
    if not resp.ok:
        raise RuntimeError(f'Currency service returned {resp.status_code}')
    xml_tree = ElementTree.fromstring(resp.text)
    try:
        exchange_rate_text = xml_tree.find(f'.//Valute[@ID="{currency_code}"]/Value').text
    except:
        raise RuntimeError(f'Invalid currency: {currency_code}')
    try:
        exchange_rate = float(exchange_rate_text.replace(',', '.'))
    except:
        raise RuntimeError(f'Invalid exchange rate format: {exchange_rate_text}')
    return exchange_rate


def get_google_api_credentials(credentials_filename):
    ''' Get cached Google API credentials or initiate a new OAuth flow if the credentials are expired.

    Parameters
    ----------
    credentials_filename : str
        Path to a JSON-file with the credentials of a registered Google API application.
    
    Returns
    -------
        `google.oauth2.credentials.Credentials`
    '''
    credentials = None
    if os.path.exists('token.json'):
        try:
            credentials = google.oauth2.credentials.Credentials.from_authorized_user_file('token.json', SCOPES)
        except:
            credentials = None
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(google.auth.transport.requests.Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(credentials_filename, SCOPES)
            credentials = flow.run_local_server(port=0)
        with open('token.json', 'w') as token_file:
            token_file.write(credentials.to_json())
    return credentials


def download_purchases_from_google_sheets(id, api_key=None, credentials=None, cell_range='B2:D'):
    ''' Download a table of purchases from Google Sheets.

    Parameters
    ----------
    id : str
        Google Sheets document ID.
    api_key : str
        Google Sheets API key (for public documents only). Used if `credentials` is not supplied.
    credentials : google.oauth2.credentials.Credentials
        Application cretentials supplied for Google Sheets API.
    cell_range : str
        Cell range (A1 or R1C1 format).
    
    Returns
    -------
        Dataframe of purсhases.
    '''
    if credentials is not None:
        service = googleapiclient.discovery.build('sheets', 'v4', credentials=credentials)
    elif api_key is not None:
        service = googleapiclient.discovery.build('sheets', 'v4', developerKey=api_key)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=id, range=cell_range).execute()
    values = result.get('values', [])
    if not values:
        raise RuntimeError('Google sheet not found')
    sheet = pd.DataFrame(values, columns=['id', 'cost_usd', 'delivery_date'])
    sheet.set_index('id', inplace=True)
    sheet.cost_usd = sheet.cost_usd.astype(float)
    sheet.delivery_date = pd.to_datetime(sheet.delivery_date, dayfirst=True)
    return sheet


def refresh_table(db_engine, update_datetime):
    ''' Delete old rows from the table.

    Parameters
    ----------
    db_engine : Engine
        Database engine.
    update_datetime : datetime
        Datetime of the last table update (all entries older than `update_datetime` are to be deleted from the table).

    Returns
    -------
        A tuple of 3 counters:
        number of rows in the table after refreshing,
        number of rows removed,
        number of rows added.
    '''
    query = f'''
        WITH
            old_purchase AS (SELECT * FROM purchase WHERE update_datetime < '{update_datetime}'),
            new_purchase AS (SELECT * FROM purchase WHERE update_datetime = '{update_datetime}'),
            purchase_mapping AS (
                SELECT old_purchase.id AS old, new_purchase.id AS new
                FROM old_purchase FULL OUTER JOIN new_purchase USING (id, cost_usd, cost_rub, delivery_date)
            )
        SELECT COUNT (*), COUNT (old), COUNT (new) FROM purchase_mapping
    '''
    result = db_engine.execute(query)
    num_rows, num_old_rows, num_new_rows = result.fetchone()
    num_removed_rows = num_rows - num_new_rows
    num_added_rows = num_rows - num_old_rows
    query = f''' DELETE FROM purchase WHERE update_datetime < '{update_datetime}' '''
    db_engine.execute(query)
    return num_new_rows, num_removed_rows, num_added_rows


def notify_overdue_purchases(db_engine, telegram_notifier):
    ''' Check for overdue purchases and notify Telegram subscribers.
    
    Parameters
    ----------
    db_engine : Engine
        Database engine.
    telegram_notifier : TelegramNotifier
        Telegram notifier instance.
    '''
    query = f'''
        SELECT purchase.* FROM purchase LEFT JOIN overdue_purchase ON purchase.id = overdue_purchase.purchase_id
        WHERE purchase.delivery_date < CURRENT_DATE AND overdue_purchase.purchase_id IS NULL
    '''
    overdue_purchases = pd.read_sql(query, db_engine, index_col='id')
    if len(overdue_purchases) > 0:
        message = 'Overdue order IDs: {}'.format(', '.join(map(str, overdue_purchases.index)))
        telegram_notifier.notify_all(message)
        query = 'INSERT INTO overdue_purchase VALUES {}'.format(', '.join(map('({})'.format, overdue_purchases.index)))
        db_engine.execute(query)


if __name__ == '__main__':
    arg_parser = ArgumentParser()
    arg_parser.add_argument('--sheet-id', help='Google sheets document ID')
    arg_parser.add_argument('--api-key', default='AIzaSyDhVhA4GpL9-DJAR1u6AzUStCY0O8yFFbI', help='Google API key')
    arg_parser.add_argument('--credentials', help='Google API app credentials')
    arg_parser.add_argument('--time-interval', type=int, default='600', help='Update frequency in seconds')
    arg_parser.add_argument('--telegram-notifier', help='Path to a Telegram notifier config file')
    arg_parser.add_argument('--max-delivery-date', help='Path to a Telegram notifier config file')
    arg_parser.add_argument('--db-name', default='canal_service', help='Database name')
    arg_parser.add_argument('--db-user', default='canal_service', help='Database user')
    arg_parser.add_argument('--db-pass', default='canal_service', help='Database user password')    
    arg_parser.add_argument('--db-host', default='localhost', help='Database host')
    arg_parser.add_argument('--db-port', default='5432', help='Database name')
    arg_parser.add_argument('--log-level', default='INFO', help='Log level')
    arg_parser.add_argument('--log-file', help='Log file')
    args = arg_parser.parse_args()

    logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
    logging.basicConfig(level=args.log_level, filename=args.log_file, format='[%(asctime)s %(levelname)s] %(message)s')

    if args.telegram_notifier is not None:
        telegram_notifier = TelegramNotifier(args.telegram_notifier)
    else:
        telegram_notifier = None

    while True:
        if args.credentials:
            credentials = get_google_api_credentials(args.credentials)
        else:
            credentials = None
        sheet = download_purchases_from_google_sheets(args.sheet_id, api_key=args.api_key, credentials=credentials)
        usd_exchange_rate = get_currency_exchange_rate(USD_CURRENCY_CODE)
        logger.info(f'RUB/USD Exchange rate: {usd_exchange_rate}')
        update_datetime = datetime.now()
        logger.info(f'Update datetime: {update_datetime}')
        sheet['cost_rub'] = (sheet.cost_usd * usd_exchange_rate).round(2)
        sheet['update_datetime'] = update_datetime
        db_url = 'postgresql+psycopg2://{}:{}@{}:{}/{}'.format(
            args.db_user, args.db_pass, args.db_host, args.db_port, args.db_name)
        db_engine = sqlalchemy.create_engine(db_url)
        sheet.to_sql('purchase', db_engine, if_exists='append')
        num_rows, num_removed_rows, num_added_rows = refresh_table(db_engine, update_datetime)
        logger.info(f'Total rows: {num_rows} ({num_removed_rows} removed, {num_added_rows} added)')
        if telegram_notifier is not None:
            notify_overdue_purchases(db_engine, telegram_notifier)
        sleep(args.time_interval)
