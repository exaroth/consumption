from core.models import metadata, engine
from core.config import DATABASE_PATH



if __name__ == "__main__":
    metadata.bind = engine
    metadata.create_all()
    print "Database Created : " +  DATABASE_PATH
