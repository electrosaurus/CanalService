import yaml
import requests
import logging

class TelegramNotifier:
    def __init__(self, config_filename):
        self.config_filename = config_filename
        with open(config_filename) as config_file:
            config = yaml.safe_load(config_file)
        self.token = config['token']
        self.chat_ids = list(map(int, config['chat_ids']))
        if config['last_update_id'] is None:
            self.last_update_id = None
        else:
            self.last_update_id = int(config['last_update_id'])
    
    def update_config(self):
        config = {
            'token': self.token,
            'last_update_id': self.last_update_id,
            'chat_ids': self.chat_ids,
        }
        with open(self.config_filename, 'w') as config_file:
            yaml.dump(config, config_file)

    def subscribe_user(self, chat_id):
        ''' Subscribe a user to notifications. '''
        if chat_id in self.chat_ids:
            return 'Already subscribed'
        else:
            self.chat_ids.append(chat_id)
            return 'Subscribed'
    
    def unsubscribe_user(self, chat_id):
        ''' Unsubscribe a user from notifications. '''
        if chat_id in self.chat_ids:
            self.chat_ids.remove(chat_id)
            return 'Unsubscribed'
        else:
            return 'Not subscribed'

    def notify_user(self, chat_id, message):
        url = f'https://api.telegram.org/bot{self.token}/sendMessage?chat_id={chat_id}&text={message}'
        return requests.get(url).json()
    
    def notify_all(self, message):
        for chat_id in self.chat_ids:
            self.notify_user(chat_id, message)

    def refresh(self):
        ''' Process new incoming messages. '''
        url = f'https://api.telegram.org/bot{self.token}/getUpdates'
        if self.last_update_id is not None:
            url += f'?offset={self.last_update_id+1}'
        resp = requests.get(url).json()
        if not resp['ok']:
            raise RuntimeError('Telegram bot error')
        for update_data in resp['result']:
            self.last_update_id = int(update_data['update_id'])
            if 'message' not in update_data:
                continue
            message_data = update_data['message']
            command = message_data['text']
            chat_id = message_data['chat']['id']
            username = message_data['from']['username']
            if command == '/subscribe':
                message = self.subscribe_user(chat_id)
                logging.info(f'Subscribed user {username}')
            elif command == '/unsubscribe':
                message = self.unsubscribe_user(chat_id)
                logging.info(f'Unsubscribed user {username}')
            else:
                message = f'Unknown command: {command}'
                logging.info(f'Unknown command "{command}" from user {username}')
            self.notify_user(chat_id, message)
        self.update_config()
