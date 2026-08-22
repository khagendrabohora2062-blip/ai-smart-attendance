from extensions import mysql


def get_cursor():
    return mysql.connection.cursor()


def commit():
    mysql.connection.commit()