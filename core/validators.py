'''
File: validators.py
Author: Konrad Wasowicz
Description: Validators for products and users
'''

import re


user_validation = re.compile("^(\w+){4,20}$") # match only letters, nymbers and '_' and only between 4 and 20 characters

def username_valid(username):
    """
    Checks if given username contains required
    characters and has proper length
    Returns bool
    """

    return bool(user_validation.search(username))


email_validation = re.compile(r'(?:^|\s)[-a-z0-9_.]+@(?:[-a-z0-9]+\.)+[a-z]{2,6}(?:\s|$)',re.IGNORECASE)

def email_valid(email):

    return bool(email_validation.search(email))

def password_valid(password):

    return len(password) in xrange(4,20)

product_validation = re.compile("^([\w+\\s*]){4,20}$")

def product_name_valid(name):

    return bool(product_validation.search(name))
