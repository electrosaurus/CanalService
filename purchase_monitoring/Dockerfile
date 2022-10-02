FROM python:latest
ADD requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY telegram_notifier.py telegram_notifier.py
COPY monitor_purchases.py monitor_purchases.py
COPY credentials.json credentials.json
CMD ["python", "-u", "monitor_purchases.py", \
    "--sheet-id", "1CUsWSQ4BnScbqBbYSuoxG_gnD9hFpk6ozSU15_3gkmY", \
    "--db-host", "db", \
    "--log-level", "INFO", \
    "--time-interval", "10"]
