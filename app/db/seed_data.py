"""Real SGN events/articles content, mirrored from sbn-website's
src/eventsData.js and src/articlesData.js catalogs so the backend and
admin panel have the same real records instead of empty tables.

Frontend-only display fields (gallery, guest, programme, collaboration,
link, sortDate, matchTitles) aren't part of the backend schema and are
intentionally omitted -- the frontend catalog remains the source of
truth for those and is merged on top of whatever this API returns.
"""

SEED_EVENTS = [
    {
        "title": "Scaleup Fireside Chat & Networking",
        "description": (
            "MULTIVERSE by code evening with Saudi tech founders in London. Fireside "
            "chat with Tom Millar (CEO, Venari Security) and Sergei Riabov (Product & "
            "Growth Advisor, ex Revolut), followed by open networking with the founder "
            "cohort."
        ),
        "date": "Tuesday, 16 June 2026",
        "time": "6:00 to 7:30 PM GMT",
        "location": "London, UK",
        "event_type": "Fireside chat",
        "price": "Invite only",
        "image_url": "/events/multiverse-scaleup-fireside.png",
        "has_happened": True,
        "published": True,
        "speakers": [
            {"name": "Tom Millar", "title": "CEO, Venari Security", "bio": ""},
            {
                "name": "Sergei Riabov",
                "title": "Product & Growth Advisor, ex Revolut",
                "bio": "",
            },
        ],
        "agenda": [
            {
                "time": "6:00 PM",
                "title": "Fireside chat",
                "speaker": "Tom Millar and Sergei Riabov",
            },
            {
                "time": "6:45 PM",
                "title": "Open networking",
                "speaker": "Scaleups, speakers, and Saudi tech founders",
            },
        ],
    },
    {
        "title": "MULTIVERSE Investor Showcase & Mixer",
        "description": (
            "Multiverse by CODE brought UK investors and Saudi tech founders together "
            "for an investor showcase and mixer as part of a government backed "
            "immersion programme in London."
        ),
        "date": "Tuesday, 2 June 2026",
        "time": "5:00 to 7:30 PM GMT",
        "location": "1 Finsbury Avenue, Broadgate, London EC2M 2PF",
        "event_type": "Showcase",
        "price": "Invite only",
        "image_url": "/events/multiverse-investor-showcase.png",
        "has_happened": True,
        "published": True,
        "speakers": [],
        "agenda": [
            {"time": "5:00 PM", "title": "Investment mandates", "speaker": "UK investment firms"},
            {"time": "6:00 PM", "title": "Networking mixer", "speaker": ""},
        ],
    },
    {
        "title": "Energy Futures Forum: Policy, Innovation & Venture Opportunities",
        "description": (
            "An afternoon exploring the UK and Saudi energy corridor across policy, "
            "innovation, and investment. Session 1 with Ahmed AlJameel on navigating "
            "the energy transition, moderated by Manal Adham. Session 2 with Reem "
            "Alsadoun and Dr Gyen Ming Angel on energy innovation and venture "
            "opportunities, moderated by Osama Alsaiari. Followed by networking."
        ),
        "date": "Sunday, 15 February 2026",
        "time": "1:00 to 5:00 PM",
        "location": "Imperial College London",
        "event_type": "Forum",
        "price": "Free",
        "image_url": "/events/energy-futures-forum.png",
        "has_happened": True,
        "published": True,
        "speakers": [
            {
                "name": "Ahmed AlJameel",
                "title": "Energy & Climate Policy · PhD Researcher, Imperial College London",
                "bio": "Nominated Technical Expert at the UNFCCC and Lead Author at the IPCC.",
            },
            {
                "name": "Reem Alsadoun",
                "title": "Energy Policy Senior Specialist",
                "bio": "MPhil in Engineering for Sustainable Development, University of Cambridge.",
            },
            {
                "name": "Dr Gyen Ming Angel",
                "title": "Managing Director, Prosemino",
                "bio": "Venture studio focused on climate and energy technology.",
            },
        ],
        "agenda": [
            {
                "time": "Session 1",
                "title": "Navigating the New Energy Transition",
                "speaker": "Ahmed AlJameel · Moderated by Manal Adham",
            },
            {
                "time": "Session 2",
                "title": "Energy Innovation and Venture Opportunities in the UK and Saudi Arabia",
                "speaker": "Reem Alsadoun and Dr Gyen Ming Angel · Moderated by Osama Alsaiari",
            },
            {"time": "Close", "title": "Networking", "speaker": ""},
        ],
    },
    {
        "title": "Innovation, Collaboration, and the Future of KSA and UK HealthTech and BioTech",
        "description": (
            "Fireside conversation with Dr Sebastian Vaughan, CEO of Phytome Life "
            "Sciences, on biotechnology, AI-enabled therapeutics, and UK and Saudi "
            "pathways in HealthTech and BioTech. Moderated by Manal Adham."
        ),
        "date": "November 2025",
        "time": "",
        "location": "London, UK",
        "event_type": "Fireside chat",
        "price": "Members",
        "image_url": "/events/healthtech-biotech.png",
        "has_happened": True,
        "published": True,
        "speakers": [
            {
                "name": "Dr Sebastian Vaughan",
                "title": "CEO, Phytome Life Sciences (UK)",
                "bio": (
                    "Guest speaker on innovation and collaboration in KSA and UK "
                    "HealthTech and BioTech."
                ),
            },
            {"name": "Manal Adham", "title": "Founder, Saudi Global Network", "bio": "Moderator."},
        ],
        "agenda": [],
    },
    {
        "title": "Misk Global Forum Majilis X , SLS UK Chapter",
        "description": (
            "A special session of the Misk Global Forum hosted by the Saudi Leadership "
            "Society UK Chapter and Saudi Global Network, asking how AI, robotics, and "
            "digital technologies can advance sustainability. Moderated by Turki "
            "Ababtain, with Aliza Ayaz and Charles Phillips."
        ),
        "date": "30 September 2025",
        "time": "5:00 to 6:30 PM",
        "location": "London, UK",
        "event_type": "Forum",
        "price": "Invite only",
        "image_url": "/events/misk-majilis-x.png",
        "has_happened": True,
        "published": True,
        "speakers": [
            {
                "name": "Aliza Ayaz",
                "title": "UN Goodwill Ambassador",
                "bio": "Sustainability consultant and founder of Climate Action Society.",
            },
            {
                "name": "Charles Phillips",
                "title": "Independent consultant",
                "bio": "Specialising in sustainable development and clean energy.",
            },
            {"name": "Turki Ababtain", "title": "Moderator", "bio": ""},
        ],
        "agenda": [],
    },
    {
        "title": "Saudi and UK Trade and Investment Opportunities",
        "description": (
            "Discussion with Abdullah AlMasoud, Saudi Commercial Attaché to the United "
            "Kingdom, on Vision 2030 investment opportunities and deepening UK and "
            "Saudi commercial collaboration."
        ),
        "date": "4 September 2025",
        "time": "6:00 to 8:00 PM",
        "location": "London, UK",
        "event_type": "Fireside chat",
        "price": "Free",
        "image_url": "/events/attache/photo-00.jpg",
        "has_happened": True,
        "published": True,
        "speakers": [
            {
                "name": "Abdullah AlMasoud",
                "title": "Saudi Commercial Attaché to the United Kingdom",
                "bio": "",
            },
        ],
        "agenda": [],
    },
    {
        "title": "Saudi British Network: Event 2",
        "description": (
            "Networking evening with the Saudi British Network community at 1 Finsbury "
            "Avenue, connecting professionals across the UK and Saudi business "
            "community."
        ),
        "date": "Wednesday, 16 April 2025",
        "time": "6:00 to 8:00 PM BST",
        "location": "1 Finsbury Avenue, Broadgate, London EC2M 2PF",
        "event_type": "Networking",
        "price": "Free",
        "image_url": "/events/sbn-event-2/photo-00.jpg",
        "has_happened": True,
        "published": True,
        "speakers": [],
        "agenda": [],
    },
    {
        "title": "Saudi Business Network: Launch Event",
        "description": (
            "The first Saudi Business Network gathering, connecting professionals, "
            "founders, and partners to open the UK and Saudi community programme."
        ),
        "date": "January 2025",
        "time": "",
        "location": "London, UK",
        "event_type": "Launch",
        "price": "Free",
        "image_url": "/events/sbn-launch/cover.jpg",
        "has_happened": True,
        "published": True,
        "speakers": [],
        "agenda": [],
    },
]

SEED_ARTICLES = [
    {
        "title": "The incomplete corridor: institutional architecture without a matching market",
        "excerpt": (
            "UK–Saudi cooperation is well endowed with frameworks and under-endowed "
            "with mechanisms that clear practitioner-level matches. A note on search "
            "costs, reputation, and the missing activation layer."
        ),
        "author": "Manal Adham",
        "category": "Research note",
        "image_url": "/articles/activation-layer.svg",
        "published": True,
        "created_at": "2026-03-01T10:00:00.000Z",
        "content": (
            "<p>The UK–Saudi relationship is often described as if proximity of interest "
            "were sufficient for coordination. Empirically, that is not how markets for "
            "collaboration behave. What we observe is a corridor with dense "
            "institutional architecture, including frameworks, missions, and MoUs, and "
            "a comparatively thin apparatus for matching the people who must execute on "
            "those ambitions.</p>"
        ),
    },
    {
        "title": "Designing for match quality: selection, repetition, and introduction capital",
        "excerpt": (
            "If the binding constraint on the UK–Saudi corridor is matching under "
            "incomplete information, network design choices matter. A short note on "
            "selection, repeated games, and why introductions should be rationed."
        ),
        "author": "Manal Adham",
        "category": "Research note",
        "image_url": "/articles/search-friction.svg",
        "published": True,
        "created_at": "2026-04-12T10:00:00.000Z",
        "content": (
            "<p>Once collaboration is framed as a matching problem rather than a "
            "messaging problem, design questions follow: who is admitted, how often do "
            "the same people meet, and what obligations attach to an introduction. Soft "
            "answers, such as \"be open\" or \"connect everyone,\" are popular and "
            "usually wrong for thin, high-stakes corridors.</p>"
        ),
    },
    {
        "title": (
            "The cross-border hire: search costs, signal, and why job boards fail thin corridors"
        ),
        "excerpt": (
            "Cross-border hiring between the UK and Saudi Arabia is not a sourcing "
            "problem. It is a search-and-verification problem under thin information, "
            "and generic job boards are built for the wrong failure mode."
        ),
        "author": "Manal Adham",
        "category": "Research note",
        "image_url": "/articles/professionals-meeting.jpg",
        "published": True,
        "created_at": "2026-06-08T10:00:00.000Z",
        "content": (
            "<p>Cross-border hiring between the UK and Saudi Arabia is usually treated "
            "as a sourcing problem: not enough candidates, not enough visibility, not "
            "enough reach. The more common failure is different. There are candidates. "
            "What is missing is a cheap way to verify, from a distance, whether a "
            "specific candidate is a specific fit.</p>"
        ),
    },
    {
        "title": (
            "Capital is not the constraint: search frictions in UK–Saudi "
            "investor-founder matching"
        ),
        "excerpt": (
            "Capital exists on both sides of the UK–Saudi corridor. Deal flow does not "
            "move at the same pace, because finding a specific, verified counterparty "
            "costs more than most investors or founders budget for it."
        ),
        "author": "Manal Adham",
        "category": "Research note",
        "image_url": "/articles/analysis.jpg",
        "published": True,
        "created_at": "2026-07-20T10:00:00.000Z",
        "content": (
            "<p>There is no shortage of capital looking for opportunities in Saudi "
            "Arabia, and no shortage of Saudi and UK founders looking for capital. The "
            "corridor's investment flow is nonetheless slower than the underlying "
            "appetite on both sides would predict. The reason is rarely deal terms. It "
            "is that finding a specific, verified counterparty costs more than either "
            "side typically budgets for.</p>"
        ),
    },
]
