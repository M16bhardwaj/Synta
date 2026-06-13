import re
import secrets
from datetime import datetime, timedelta

from itsdangerous import BadSignature, URLSafeSerializer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import Response

from syntra.core.config import get_settings
from syntra.db.models import MemberRole, User, Workspace, WorkspaceMember

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def slugify_workspace(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "workspace"


class AuthService:
    cookie_name = "syntra_session"

    def __init__(self, session: Session):
        self.session = session
        settings = get_settings()
        secret = settings.encryption_key or settings.llm_api_key or settings.github_token
        self.serializer = URLSafeSerializer(secret or "syntra-local-development-secret")

    def create_user(self, email: str, name: str, password: str, workspace_name: str) -> User:
        existing = self.session.scalar(select(User).where(User.email == email.lower()))
        if existing:
            raise ValueError("A user with this email already exists.")

        user = User(
            email=email.lower(),
            name=name,
            password_hash=pwd_context.hash(password),
            email_verification_token=secrets.token_urlsafe(32),
        )
        workspace = Workspace(
            name=self._unique_workspace_name(workspace_name),
            slug=self._unique_workspace_slug(workspace_name),
        )
        self.session.add_all([user, workspace])
        self.session.flush()
        self.session.add(
            WorkspaceMember(user_id=user.id, workspace_id=workspace.id, role=MemberRole.OWNER)
        )
        self.session.commit()
        self.session.refresh(user)
        return user

    def verify_email(self, token: str) -> User:
        user = self.session.scalar(select(User).where(User.email_verification_token == token))
        if not user:
            raise ValueError("Verification link is not valid.")
        user.email_verified = True
        user.email_verification_token = None
        self.session.commit()
        self.session.refresh(user)
        return user

    def create_password_reset(self, email: str) -> User | None:
        user = self.session.scalar(select(User).where(User.email == email.lower()))
        if not user:
            return None
        user.password_reset_token = secrets.token_urlsafe(32)
        user.password_reset_expires_at = datetime.utcnow() + timedelta(hours=2)
        self.session.commit()
        self.session.refresh(user)
        return user

    def reset_password(self, token: str, password: str) -> User:
        user = self.session.scalar(select(User).where(User.password_reset_token == token))
        if not user or not user.password_reset_expires_at:
            raise ValueError("Reset link is not valid.")
        expires_at = user.password_reset_expires_at.replace(tzinfo=None)
        if expires_at < datetime.utcnow():
            raise ValueError("Reset link has expired.")
        user.password_hash = pwd_context.hash(password)
        user.password_reset_token = None
        user.password_reset_expires_at = None
        self.session.commit()
        self.session.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> User | None:
        user = self.session.scalar(select(User).where(User.email == email.lower()))
        if not user or not pwd_context.verify(password, user.password_hash):
            return None
        return user

    def login(self, response: Response, user: User) -> None:
        token = self.serializer.dumps({"user_id": user.id})
        response.set_cookie(
            self.cookie_name,
            token,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 14,
        )

    def logout(self, response: Response) -> None:
        response.delete_cookie(self.cookie_name)

    def current_user(self, request: Request) -> User | None:
        token = request.cookies.get(self.cookie_name)
        if not token:
            return None
        try:
            data = self.serializer.loads(token)
        except BadSignature:
            return None
        return self.session.get(User, data.get("user_id"))

    def current_workspace(self, user: User) -> Workspace | None:
        membership = self.session.scalar(
            select(WorkspaceMember).where(WorkspaceMember.user_id == user.id)
        )
        return membership.workspace if membership else None

    def _unique_workspace_slug(self, workspace_name: str) -> str:
        base = slugify_workspace(workspace_name)
        slug = base
        index = 2
        while self.session.scalar(select(Workspace).where(Workspace.slug == slug)):
            slug = f"{base}-{index}"
            index += 1
        return slug

    def _unique_workspace_name(self, workspace_name: str) -> str:
        name = workspace_name
        index = 2
        while self.session.scalar(select(Workspace).where(Workspace.name == name)):
            name = f"{workspace_name} {index}"
            index += 1
        return name
