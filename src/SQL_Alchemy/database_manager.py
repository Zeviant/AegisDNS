from src.SQL_Alchemy.database import User, Addresses, session 
from datetime import datetime

class DatabaseManager:
    """
    Manages all user-related database operations using SQLAlchemy session.
    """

    @staticmethod
    def authenticate_user(username: str, password: str) -> bool:
        """
        Checks if a user exists with the given username and password.
        Returns True on successful login, False otherwise.
        """
        user = session.query(User).filter_by(password=password).where(User.user_name==username).first()
        return user is not None

    @staticmethod
    def create_new_user(username: str, password: str, firstName: str, lastName: str) -> str:
        """
        Attempts to create a new user.
        Returns:
            "success": if user was created.
            "taken": if username already exists.
            "error": on an unexpected database error.
        """
        try:
            if session.query(User).filter_by(user_name=username).first():
                return "taken"

            user_placement = User(username, password, firstName, lastName)
            session.add(user_placement)
            session.commit()
            return "success"
        except Exception:
            session.rollback() 
            return "error"
            
    @staticmethod
    def update_password(username: str, current_password: str, new_password: str) -> str:
        try:
            user = session.query(User).filter_by(user_name=username).first()
            if not user:
                return "error"
            
            if user.password != current_password:
                return "wrong_password"
            
            user.password = new_password
            session.commit()
            return "success"
        except Exception:
            session.rollback()
            return "error"
            
    @staticmethod
    def update_username(old_username: str, current_password: str, new_username: str) -> str:

        try:
            user = session.query(User).filter_by(user_name=old_username).first()
            if not user:
                return "error"
            
            if user.password != current_password:
                return "wrong_password"
            
            # Check if new username already exists
            if session.query(User).filter_by(user_name=new_username).first():
                return "taken"
            
            # Create the new user first (needed for foreign key constraint)
            new_user = User(new_username, user.password, user.first_name, user.last_name)
            session.add(new_user)

            # Flush to make new user available for foreign key references
            session.flush()
            
            # Update all Addresses records that reference this user
            addresses = session.query(Addresses).filter_by(owner=old_username).all()
            for addr in addresses:
                addr.owner = new_username
            
            # Delete the old user
            session.delete(user)
            session.commit()
            return "success"
        except Exception:
            session.rollback()
            return "error"
            
    @staticmethod
    def delete_user(username: str, password: str) -> str:
        try:
            user = session.query(User).filter_by(user_name=username).first()
            if not user:
                return "error"
            
            if user.password != password:
                return "wrong_password"
            
            # Delete all Addresses records that reference this user
            addresses = session.query(Addresses).filter_by(owner=username).all()
            for addr in addresses:
                session.delete(addr)
            
            # Delete the user
            session.delete(user)
            session.commit()
            return "success"
        except Exception:
            session.rollback()
            return "error"
            
    @staticmethod
    def log_address_scan(target: str, verdict: str, userName: str) -> None:
        """
        Logs a completed scan result to the 'addresses' table.
        """
        try:
            # Check if address already exists
            existing_address = session.query(Addresses).filter_by(address=target).first()
            
            if existing_address:
                # Update existing record
                existing_address.date = datetime.now()
                existing_address.verdict = verdict
                existing_address.owner = userName
            else:
                # Create new record
                address = Addresses(target, datetime.now(), verdict, owner=userName)
                session.add(address)
            
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error logging scan history to DB: {e}")