import os


class Config:
    if not 'WEBSITE_HOSTNAME' in os.environ:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///./test.db'
    else:
        SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://{dbuser}:{dbpass}@{dbhost}/{dbname}'.format(
            dbuser=os.environ['DBUSER'],
            dbpass=os.environ['DBPASS'],
            dbhost=os.environ['DBHOST'] + ".postgres.database.azure.com",
            dbname=os.environ['DBNAME'])

        JWT_SECRET_KEY = os.environ['JWT_SECRET_KEY']

    JWT_ACCESS_TOKEN_EXPIRES = 12000


class Configtesting:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///./test_db.db'
    JWT_SECRET_KEY = 'test'
