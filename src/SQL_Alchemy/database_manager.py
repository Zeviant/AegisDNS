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
        """
        Updates a user's password after verifying the current password.
        Returns:
            "success": if password was updated successfully.
            "wrong_password": if current password is incorrect.
            "error": on an unexpected database error.
        """
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