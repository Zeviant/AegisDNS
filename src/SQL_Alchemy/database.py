from sqlalchemy import Column, Integer, String, ForeignKey, Sequence, CHAR, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from pathlib import Path

# Create an engine that stores data in the local directory's
# sqlalchemy_example.db file.

# Create a declarative base class
Base = declarative_base()

class User(Base): 
    __tablename__ = "users"

    user_name = Column("UserName", String, primary_key = True) # Unique Value
    password = Column("Password", String)

    def __init__(self, username, passw): 
        self.user_name = username
        self.password = passw
    
    def __repr__(self): 
        return f"({self.user_name} {self.password})"

class Addresses(Base):
    __tablename__ = "addresses"
    address = Column("Address", String, primary_key = True)
    date = Column("Date", Integer) # Change integer for the proper date vairable type
    owner = Column(String, ForeignKey("users.UserName")) # Here connects the user with the URL he searched

    def __init__(self, addr, date, owner): 
        self.address = addr
        self.date = date
        self.owner = owner
    
    def __repr__(self): 
        return f"({self.address} {self.date} {self.owner})"

# Creating the engine
# Resolve base directory (this file is inside src/SQL_Alchemy)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "UserInformation.db"

engine = create_engine(f"sqlite+pysqlite:///{DB_PATH}", echo=True) # This creates the database's file
Base.metadata.create_all(bind=engine) # This creates the tables inside the database 


# Session allows to do all kind of things 
Session = sessionmaker(bind=engine)
session = Session()

# Only added once
if not session.query(User).first():
    user = User("Nico", "asdf") # Creates user
    session.add(user) # Adds user to the database
    session.commit() # Applies the changes to the database


