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

def generate_secure_cookie(username):
    """
    NOTE: this cookie is not at all secure
    generates cookie based on username and secret_key
    """

    return hashlib.sha1(username + ";session;" + SECRET_KEY).hexdigest()

def check_secure_cookie(cookie, username):
    """
    Validates the cookie 
    """

    return cookie == generate_secure_cookie(username)



