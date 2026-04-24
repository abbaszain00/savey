import bcrypt


def hash_password(password: str) -> str:
    # Generates a salt and hashes the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    # Checks if the provided password matches the stored hash
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
