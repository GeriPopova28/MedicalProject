from flask import config, g
import mysql


def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(**config)
    return g.db