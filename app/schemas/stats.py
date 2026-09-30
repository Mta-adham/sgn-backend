from datetime import datetime

from pydantic import BaseModel


class MessagesBreakdown(BaseModel):
    new: int = 0
    replied: int = 0
    closed: int = 0


class TierCount(BaseModel):
    tier: str
    count: int


class CategoryCount(BaseModel):
    category: str
    count: int


class RecentMember(BaseModel):
    id: int
    name: str
    email: str
    membership_tier: str
    active: bool
    created_at: datetime


class UpcomingEventStat(BaseModel):
    id: int
    title: str
    date: str | None = None
    rsvp_count: int


class ConnectorStat(BaseModel):
    """One member's connection activity, for the leaderboards."""

    id: int
    name: str
    email: str
    count: int


class ConnectionStats(BaseModel):
    """How the connections feature is actually being used.

    Counts alone say little. The ratios are what tell you whether the feature is working:
    a high request count with a low acceptance rate means people are being approached by
    the wrong members, which is a directory problem rather than a connections problem.
    """

    total_requests: int = 0
    accepted: int = 0
    declined: int = 0
    pending: int = 0
    reported: int = 0

    # Of the requests that got an answer, how many were yes. Pending ones are excluded
    # because counting them as failures would understate a young feature.
    acceptance_rate: float | None = None
    # Requests still waiting after a week. The number nobody wants to grow.
    stale_pending: int = 0
    median_response_hours: float | None = None

    requests_30d: int = 0
    requests_prev_30d: int = 0
    accepted_30d: int = 0

    # Members who have connected with at least one other member. The share of the
    # directory that has actually used it.
    members_with_connections: int = 0
    directory_eligible: int = 0

    most_connected: list[ConnectorStat] = []
    most_requested: list[ConnectorStat] = []

    open_reports: int = 0
    total_reports: int = 0


class StatsOut(BaseModel):
    # Totals
    total_members: int
    total_articles: int
    total_events: int
    active_events: int
    messages_breakdown: MessagesBreakdown

    # Membership growth: current 30-day window vs the 30 days before it, so the dashboard
    # can show direction of travel rather than a bare number.
    new_members_30d: int = 0
    new_members_prev_30d: int = 0
    new_members_7d: int = 0

    # Network health
    active_members: int = 0
    blocked_members: int = 0
    members_by_tier: list[TierCount] = []
    members_by_category: list[CategoryCount] = []
    uncategorised_members: int = 0

    # Engagement
    total_rsvps: int = 0
    rsvps_30d: int = 0
    rsvps_prev_30d: int = 0
    directory_opt_in: int = 0
    upcoming_events: list[UpcomingEventStat] = []

    # Connections
    connections: ConnectionStats = ConnectionStats()

    # Recent activity feed
    recent_members: list[RecentMember] = []
