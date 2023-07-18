import random
import string
from datetime import datetime

def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_letters + string.digits
    result_str = ''.join(random.choice(letters) for i in range(length))
    # return result_str + datetime.strptime("%Y%d%m%H%M%S%f")
    return result_str