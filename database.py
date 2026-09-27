import json
import os
from functools import lru_cache

import boto3
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Only the secret's *name* lives in the environment; the credentials themselves
# stay in AWS Secrets Manager.
DB_SECRET_NAME = os.getenv("DB_SECRET_NAME", "dev-db-credentials")
AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")


class Base(DeclarativeBase):
    pass


@lru_cache
def get_db_secret() -> dict:
    client = boto3.client("secretsmanager", region_name=AWS_REGION)
    response = client.get_secret_value(SecretId=DB_SECRET_NAME)
    return json.loads(response["SecretString"])


@lru_cache
def get_engine():
    secret = get_db_secret()
    # URL.create escapes special characters in the password, which RDS-generated
    # passwords often contain.
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=secret["username"],
        password=secret["password"],
        host=secret.get("host") or os.environ["DB_HOST"],
        port=int(secret.get("port") or os.getenv("DB_PORT", 5432)),
        database=secret.get("dbname", "dev-db"),
    )
    return create_engine(url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker():
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db():
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()
