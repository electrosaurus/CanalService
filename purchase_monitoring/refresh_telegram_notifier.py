from argparse import ArgumentParser
from telegram_notifier import TelegramNotifier
import logging

if __name__ == '__main__':
    arg_parser = ArgumentParser()
    arg_parser.add_argument('--config', default='telegram_notifier_config.yaml')
    arg_parser.add_argument('--log-level', default='ERROR')
    args = arg_parser.parse_args()

    logging.basicConfig(level=args.log_level, format='[%(asctime)s %(levelname)s] %(message)s')

    telegram_notifier = TelegramNotifier(args.config)
    telegram_notifier.refresh()
