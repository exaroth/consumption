import hashlib
from config import SECRET_KEY



def generate_password_hash(password):

    """
    Generates password using sha1 algorithm 
    """

    return hashlib.sha1(password + "," + SECRET_KEY).hexdigest()

def check_password_hash(password, signature):
    """
    Verifies that hash matches password 
    """

    return signature == generate_password_hash(password)

