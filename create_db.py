from core.models import metadata, engine



if __name__ == "__main__":
    metadata.bind = engine
    metadata.create_all()
