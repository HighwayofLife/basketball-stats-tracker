"""Authentication service for user management."""

from datetime import datetime

from sqlalchemy.orm import Session

from .jwt_handler import create_access_token, create_refresh_token, get_password_hash, verify_password
from .models import User, UserRole


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: Session):
        """Initialize the auth service.

        Args:
            db: Database session
        """
        self.db = db

    def create_user(
        self, username: str, email: str, password: str, full_name: str | None = None, role: UserRole = UserRole.USER
    ) -> User:
        """Create a new user.

        Args:
            username: Username
            email: Email address
            password: Plain text password
            full_name: Optional full name
            role: User role (defaults to USER)

        Returns:
            Created user object

        Raises:
            ValueError: If username or email already exists
        """
        # Check for existing username
        if self.db.query(User).filter(User.username == username).first():
            raise ValueError(f"Username '{username}' already exists")

        # Check for existing email
        if self.db.query(User).filter(User.email == email).first():
            raise ValueError(f"Email '{email}' already exists")

        # Create new user
        hashed_password = get_password_hash(password)
        user = User(username=username, email=email, hashed_password=hashed_password, full_name=full_name, role=role)

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def authenticate_user(self, username: str, password: str) -> User | None:
        """Authenticate a user by username and password.

        Args:
            username: Username or email
            password: Plain text password

        Returns:
            User object if authentication successful, None otherwise
        """
        # Try to find user by username or email
        user = self.db.query(User).filter((User.username == username) | (User.email == username)).first()

        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        # Update last login
        user.last_login = datetime.utcnow()
        self.db.commit()

        return user

    def get_user_by_id(self, user_id: int) -> User | None:
        """Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User object if found, None otherwise
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, username: str) -> User | None:
        """Get user by username.

        Args:
            username: Username

        Returns:
            User object if found, None otherwise
        """
        return self.db.query(User).filter(User.username == username).first()

    def update_user_password(self, user_id: int, new_password: str) -> bool:
        """Update user password.

        Args:
            user_id: User ID
            new_password: New plain text password

        Returns:
            True if successful, False otherwise
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.hashed_password = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        self.db.commit()

        return True

    def update_user_role(self, user_id: int, new_role: UserRole) -> bool:
        """Update user role.

        Args:
            user_id: User ID
            new_role: New user role

        Returns:
            True if successful, False otherwise
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.role = new_role
        user.updated_at = datetime.utcnow()
        self.db.commit()

        return True

    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user.

        Args:
            user_id: User ID

        Returns:
            True if successful, False otherwise
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_active = False
        user.updated_at = datetime.utcnow()
        self.db.commit()

        return True

    def create_tokens(self, user: User) -> dict[str, str]:
        """Create access and refresh tokens for a user.

        Args:
            user: User object

        Returns:
            Dictionary with access_token and refresh_token
        """
        access_token_data = {"sub": str(user.id), "username": user.username, "role": user.role.value}
        refresh_token_data = {"sub": str(user.id)}

        access_token = create_access_token(access_token_data)
        refresh_token = create_refresh_token(refresh_token_data)

        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
