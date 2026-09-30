# Server-side mirror of the tier prices defined in sbn-website's src/Member.js.
# Used to independently validate payment amounts rather than trusting client input.
MEMBERSHIP_TIER_PRICES_GBP: dict[str, float] = {
    "Basic Membership": 0,
    "Premium Membership": 490,
    "Corporate Membership": 950,
}
