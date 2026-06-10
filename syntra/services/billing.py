from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from syntra.db.models import Subscription, SubscriptionStatus, Workspace


@dataclass(frozen=True)
class Plan:
    code: str
    name: str
    price: str
    repo_limit: int
    fixes_per_month: int


PLANS = [
    Plan("free", "Free", "$0", 1, 10),
    Plan("pro", "Pro", "$29/mo", 10, 200),
    Plan("team", "Team", "$99/mo", 50, 1000),
]


class BillingService:
    def __init__(self, session: Session):
        self.session = session

    def subscription_for(self, workspace_id: int) -> Subscription:
        subscription = self.session.scalar(
            select(Subscription).where(Subscription.workspace_id == workspace_id)
        )
        if subscription:
            return subscription
        subscription = Subscription(
            workspace_id=workspace_id,
            plan="free",
            status=SubscriptionStatus.TRIAL,
        )
        self.session.add(subscription)
        self.session.commit()
        self.session.refresh(subscription)
        return subscription

    def change_plan(self, workspace: Workspace, plan: str) -> Subscription:
        if plan not in {item.code for item in PLANS}:
            raise ValueError("Unknown plan.")
        subscription = self.subscription_for(workspace.id)
        subscription.plan = plan
        subscription.status = SubscriptionStatus.ACTIVE if plan != "free" else SubscriptionStatus.TRIAL
        workspace.plan = plan
        self.session.commit()
        self.session.refresh(subscription)
        return subscription
