import sqlite3


DEFAULT_CONFIG_FILE = "gitbak.conf.sqlite"


class ConfigManager:
    def __init__(self, filename=DEFAULT_CONFIG_FILE):
        self.config = sqlite3.connect(DEFAULT_CONFIG_FILE)

    def add_source(self, source):
        self.config.execute("INSERT INTO sources (url) VALUES (%s)", source)
