FROM python:latest
ADD requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY api.py api.py
EXPOSE 5000
ENTRYPOINT ["python", "-u", "api.py", "--db-host", "db"]
