# Инструкция по запуску тестового задания

Описание задания: https://unwinddigital.notion.site/unwinddigital/Python-1fdcee22ef5345cf82b058c333818c08

## Подготовка Postgres

Создадим новую базу данных и нового пользователя:
```shell
$ psql
username=# CREATE DATABASE canal_service;
username=# CREATE USER canal_service WITH PASSWORD 'canal_service';
username=# GRANT ALL PRIVILEGES ON DATABASE canal_service TO canal_service;
```

Создадим необходимые сущности:
```shell
$ psql -U canal_service -d canal_service -f init.sql
```

## Мониторинг Google-таблицы (задания 1, 2, 3)

Будем использовать таблицу, находящуюся в открытом доступе по ссылке:
https://docs.google.com/spreadsheets/d/1CUsWSQ4BnScbqBbYSuoxG_gnD9hFpk6ozSU15_3gkmY.

Перейдём в нужную директорию и установим необходимые зависимости:
```shell
$ cd purchase_monitoring
$ pip install -r requirements.txt
```

Запустим скрипт:
```shell
$ python monitor_purchases.py --sheet-id 1CUsWSQ4BnScbqBbYSuoxG_gnD9hFpk6ozSU15_3gkmY --log-level INFO --time-interval 10
```

Он будет каждые 10 секунд проверять таблицу, обновляя данные в базе и выводя в консоль логи вида:
```
[2022-10-01 00:35:50,873 INFO] RUB/USD Exchange rate: 55.2987
[2022-10-01 00:35:50,874 INFO] Update datetime: 2022-10-01 00:35:50.874017
[2022-10-01 00:35:51,152 INFO] Total rows: 50 (0 removed, 50 added)
```

`Total rows` — текущее количество строк в таблице; `removed` и `added` — количество удаленных и добавленных строк по
сравнению с предыдущим состоянием.

Посмотрим таблицу в базе данных:
```
$ psql -U canal_service -d canal_service -c "SELECT * FROM purchase LIMIT 5"
   id    |      update_datetime       | cost_usd  |  cost_rub  | delivery_date 
---------+----------------------------+-----------+------------+---------------
 1249708 | 2022-10-01 00:37:48.323595 |   $675.00 | $37,326.62 | 2022-05-24
 1182407 | 2022-10-01 00:37:48.323595 |   $214.00 | $11,833.92 | 2022-05-13
 1120833 | 2022-10-01 00:37:48.323595 |   $610.00 | $33,732.21 | 2022-05-05
 1060503 | 2022-10-01 00:37:48.323595 | $1,804.00 | $99,758.85 | 2022-05-29
 1617397 | 2022-10-01 00:37:48.323595 |   $423.00 | $23,391.35 | 2022-05-26
(5 rows)
```

- Колонка `update_datetime` хранит время обновления таблицы.
- Колонка `cost_rub` автоматически вычисляется на основе текущего курса рубля к доллару при каждом обновлении.
    Значение курса берется с сервиса https://www.cbr.ru/development/SXML/.

В примере выше для доступа к Google-таблице использовался стандартный API-ключ.
В случае если таблица не находится в свободном доступе (отключён доступ по ссылке), следует использовать
OAuth-авторизацию.
Для этого нужно указать скрипту файл с реквизитами приложения:

```shell
$ python monitor_purchases.py --sheet-id 1CUsWSQ4BnScbqBbYSuoxG_gnD9hFpk6ozSU15_3gkmY --log-level INFO --time-interval 10 --credentials credentials.json
```

При первом запуске скрипт выведет ссылку на авторизацию в Google.
Надо пройти по этой ссылке и авторизоваться как тестовый пользователь (amkolotov@gmail.com добавлен в список
тестовых пользователей).
После этого скрипт продолжит работу.
При повторном запуске скрипта авторизация уже на понадобится, поскольку полученные реквизиты сохранятся в файле `token.json`.

Описание опций скрипта можно посмотреть, вызвав команду
```shell
$ python monitor_purchases.py --help
```

## Уведомление о просроченных поставках через Telegram (задание 4.b)

Чтобы подписаться на рассылку о просроченных поставках, нужно найти в Telegram бота
[@canal_service_2_bot](https://t.me/canal_service_2_bot) и отправить ему сообщение с текстом "/subscribe".
После этого нужно запустить скрипт для обработки непрочитанных сообщений:
```
$ python refresh_telegram_notifier.py --log-level INFO
```
ID чата и ID последнего прочитанного сообщения сохранятся в файле конфигурации `telegram_notifier_config.yaml`.

На рассылку может подписаться сразу несколько людей.
Для отписки от рассылки нужно написать боту "/unsubscribe" и так же запустить скрипт.

Чтобы активировать рассылку, нужно передать скрипту файл конфигурации Telegram-бота:
```shell
$ python monitor_purchases.py --sheet-id 1CUsWSQ4BnScbqBbYSuoxG_gnD9hFpk6ozSU15_3gkmY --log-level INFO --time-interval 10 --telegram-notifier telegram_notifier_config.yaml
```
В случае если в таблице имеются просроченные поставки (дата поставки меньше нынешней даты), бот пришлёт всем
подписчикам сообщение вида:
```
Overdue order IDs: 1249708, 1182407, 1120833, ...
```

Бот запоминает, о каких просроченных поставках он сообщил, и не сообщает о них повторно.
Чтобы бот забыл об этих поставках, нужно очистить соответствующую таблицу:
```shell
$ psql -U canal_service -d canal_service -c "DELETE FROM overdue_purchase"
```

## Одностраничное приложение (задание 4.c)

В данном задании реализован только backend (REST API на основе Flask).

Перейдем в нужную директорию и установим необходимые зависимости:
```shell
$ cd ../api
$ pip install -r requirements.txt
```

Запустим сервис:
```shell
python api.py
```

Сервис будет поднят по адресу http://127.0.0.1:5000.
Он содержит два эндпоинта:
- `/purchases/` — получение списка закупок (может принимать параметры `limit` и `offset`).
- `/purchase/{id}` — получение конкретной закупки.

Примеры использования:
```shell
$ curl "http://127.0.0.1:5000/purchases/?limit=2"
[
    {
        "cost_usd": "$675.00",
        "delivery_date": "2022-05-24",
        "id": 1249708,
        "update_datetime": "2022-10-01T05:37:20.541936",
        "cost_rub": "$37,326.62"
    },
    {
        "cost_usd": "$214.00",
        "delivery_date": "2022-05-13",
        "id": 1182407,
        "update_datetime": "2022-10-01T05:37:20.541936",
        "cost_rub": "$11,833.92"
    }
]
$ curl "http://127.0.0.1:5000/purchases/?limit=1&offset=5"
[
    {
        "cost_usd": "$682.00",
        "delivery_date": "2022-05-02",
        "id": 1135905,
        "update_datetime": "2022-10-01T05:37:20.541936",
        "cost_rub": "$37,713.71"
    }
]
$ curl "http://127.0.0.1:5000/purchase/1135905"
{
    "cost_usd": "$682.00",
    "delivery_date": "2022-05-02",
    "id": 1135905,
    "update_datetime": "2022-10-01T05:37:20.541936",
    "cost_rub": "$37,713.71"
}
```

## Упаковка в Docker-контейнер (задание 4.a)

Вернёмся в корневую директорию:
```shell
$ cd ..
```

Соберем контейнеры:
```
$ docker-compose build
```

Запустим их:
```
docker-compose up
```

В результате будут одновременно запущены три контейнера:
- Postgres;
- Скрипт, обновляющий таблицу;
- API.
