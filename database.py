import json
import os
from functools import lru_cache

import boto3
from sqlalchemy import URL, create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Only the secret's *name* lives in the environment; the credentials themselves
# stay in AWS Secrets Manager. Host and database name aren't secret, and the
# RDS-managed secret only contains username + password anyway.
DB_SECRET_NAME = os.getenv("DB_SECRET_NAME", "rds!db-7c97f9e2-fac5-4f0b-9bf6-324cdfaf6fec")
AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")
DB_HOST = os.getenv("DB_HOST", "dev-db.c7qmime6ialv.eu-north-1.rds.amazonaws.com")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "postgres")


class Base(DeclarativeBase):
    pass


def get_db_secret() -> dict:
    client = boto3.client("secretsmanager", region_name=AWS_REGION)
    response = client.get_secret_value(SecretId=DB_SECRET_NAME)
    return json.loads(response["SecretString"])


@lru_cache
def get_engine():
    url = URL.create(
        drivername="postgresql+psycopg2",
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        # connect_timeout makes network problems fail with an error instead of hanging.
        query={"sslmode": "require", "connect_timeout": "10"},
    )
    engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600)

    # RDS rotates the password in its managed secret, so fetch fresh credentials
    # every time the pool opens a new connection instead of caching them forever.
    @event.listens_for(engine, "do_connect")
    def provide_credentials(dialect, conn_rec, cargs, cparams):
        secret = get_db_secret()
        cparams["user"] = secret["username"]
        cparams["password"] = secret["password"]

    return engine


@lru_cache
def get_sessionmaker():
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db():
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()
