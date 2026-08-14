import os
from pathlib import Path

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

# Create a declarative base class
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    user_name = Column("UserName", String, primary_key=True)  # Unique Value
    password = Column("Password", String)
    first_name = Column("FirstName", String)
    last_name = Column("LastName", String)

    def __init__(self, username, passw, fname, lname):
        self.user_name = username
        self.password = passw
        self.first_name = fname
        self.last_name = lname

    def __repr__(self):
        return f"({self.user_name} {self.password} {self.first_name} {self.last_name})"


class Addresses(Base):
    __tablename__ = "addresses"
    address = Column("Address", String, primary_key=True)
    date = Column("Date", DateTime)
    verdict = Column("Verdict", String)
    owner = Column(String, ForeignKey("users.UserName"))  # Connects the user with the URL they searched

    def __init__(self, addr, date, verdict, owner):
        self.address = addr
        self.date = date
        self.verdict = verdict
        self.owner = owner

    def __repr__(self):
        return f"({self.address} {self.date} {self.verdict} {self.owner})"


# --- Path resolution ---
# DB_PATH is env-configurable so this same code works both in the native dev layout
# (src/SQL_Alchemy/UserInformation.db) and inside the backend container, where it's
# pointed at a mounted volume (e.g. /data/db/UserInformation.db) so the data survives
# container recreation.
_DEFAULT_DB_PATH = Path(__file__).resolve().parent / "UserInformation.db"
DB_PATH = Path(os.getenv("DB_PATH", str(_DEFAULT_DB_PATH)))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# SQL_ECHO defaults to off — the original code had echo=True, which logs every
# statement to stdout; noisy in a container's logs, so it's now opt-in.
_SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() in ("1", "true", "yes")

engine = create_engine(f"sqlite+pysqlite:///{DB_PATH}", echo=_SQL_ECHO)
Base.metadata.create_all(bind=engine)

# Scoped session: gives each thread (i.e. each Flask request, under threaded=True)
# its own Session instance instead of sharing one global Session across concurrent
# requests, which the original single module-level `session` object did not do
# safely.
Session = scoped_session(sessionmaker(bind=engine))
session = Session
