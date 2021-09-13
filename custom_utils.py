import string
import secrets

alphabet = string.ascii_letters + string.digits
secure_rng = secrets.SystemRandom()

# generate a random string of ascii and numbers of length
def random_id(length: int) -> str:
    return ''.join(secrets.choice(alphabet) for i in range(length))
