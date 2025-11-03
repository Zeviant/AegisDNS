from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, create_engine, select
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
    address = Column("Address", String, primary_key = True)
    date = Column("Date", DateTime) 
    verdict = Column("Verdict", String) 
    owner = Column(String, ForeignKey("users.UserName")) # Here connects the user with the URL he searched

    def __init__(self, addr, date, verdict,owner): 
        self.address = addr
        self.date = date
        self.verdict = verdict
        self.owner = owner
    
    def __repr__(self): 
        return f"({self.address} {self.date} {self.verdict} {self.owner})"

# Creating the engine
# Resolve base directory (this file is inside src/SQL_Alchemy)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "UserInformation.db"

engine = create_engine(f"sqlite+pysqlite:///{DB_PATH}", echo=True) # This creates the database's file
Base.metadata.create_all(bind=engine) # This creates the tables inside the database 

# Session allows to do all kind of things 
Session = sessionmaker(bind=engine)
session = Session()

if not session.query(User).first(): # Retrieves the first element in the database
    user = User("Nico", "asdf", "Francisco", "Vega") # Creates user
    session.add(user) # Adds user to the database
    session.commit() # Applies the changes to the database

# Drop table
# Addresses.__table__.drop(engine)

# print("asdfasdfasdf")
# user = session.query(User).filter_by(user_name="Nico").first()
# if user:
#     print(user.user_name, user.password)