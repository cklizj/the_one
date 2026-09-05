"""Demo data: realistic items across domains + backdated attempts for trying the CLI."""

DOMAINS = ["algo", "cpp", "quant", "system_design", "behavioral"]

DEMO_ITEMS: list[dict] = [
    {
        "title": "Two Sum",
        "domain": "algo",
        "tags": ["leetcode", "hashmap"],
        "subquestions": [
            "What's the brute-force complexity?",
            "Why does a hash map give O(n)?",
        ],
        "notes": "key -> index seen so far; one pass.",
        "code": "seen = {}\nfor i, v in enumerate(nums):\n    if t - v in seen: return [seen[t-v], i]\n    seen[v] = i",
        "link": ["https://github.com/you/leetcode-solutions/blob/main/0001-two-sum.py"],
    },
    {
        "title": "Segment tree build / query",
        "domain": "algo",
        "tags": ["leetcode", "segment-tree"],
        "subquestions": [
            "What state does each node store?",
            "How do nodes merge?",
            "What are the bounds of a recursive query?",
        ],
        "notes": "build O(n); query/update O(log n). Recursive midpoint decomposition.",
        "code": "def build(a, n):\n    t = [0]*(4*n)\n    ...  # leaves then push up",
        "approach": "Think recursively: node = answer for its segment; merge = combine two children. "
                    "Algo: build from leaves up, split at midpoint (l+r)//2.",
        "related": ["fenwick-tree", "range-query", "binary-indexed-tree"],
        "media": [],
    },
    {
        "title": "Virtual functions & vtable",
        "domain": "cpp",
        "tags": ["cpp", "memory-layout"],
        "subquestions": [
            "Where is the vptr stored per instance?",
            "When is the vtable layout fixed?",
            "Why can constructors not call virtual dispatch?",
        ],
        "notes": "One vptr per object; vtable per class. Devirtualization opportunities abound.",
        "code": "",
        "approach": "Every object that has virtual functions carries a hidden vptr (first member) "
                    "pointing to its class's vtable; dispatch = deref vptr -> slot.",
        "related": ["RAII", "dynamic-casting", "memory-layout"],
        "media": ["~/notes/vtable-diagram.png"],
    },
    {
        "title": "RAII and unique_ptr ownership",
        "domain": "cpp",
        "tags": ["cpp", "memory"],
        "subquestions": [
            "What does unique_ptr do on scope exit?",
            "When do you reach for shared_ptr instead?",
            "What's a common cause of weak_ptr use?",
        ],
        "notes": "Ownership = lifetime management by scope.",
        "code": "std::unique_ptr<Foo> p = std::make_unique<Foo>();",
    },
    {
        "title": "Monty Hall paradox",
        "domain": "quant",
        "tags": ["brainteasers", "probability"],
        "subquestions": [
            "Write the switch/keep decision as conditional probabilities.",
            "What changes with N doors instead of 3?",
        ],
        "notes": "Host's reveal is constrained information, not noise.",
        "code": "",
    },
    {
        "title": "Design a URL shortener",
        "domain": "system_design",
        "tags": ["design", "scale"],
        "subquestions": [
            "Roughly how many writes/sec and reads/sec at 100M URLs/mo?",
            "Single-table UUID or incrementing id? Collision story?",
            "Where does caching sit and what's the eviction policy?",
        ],
        "notes": "Read-heavy; cache hot short codes; base62 ids.",
        "code": "",
        "link": ["https://github.com/you/sys-design/blob/main/url-shortener.md"],
    },
    {
        "title": "A time a project failed",
        "domain": "behavioral",
        "tags": ["star", "failure"],
        "subquestions": [
            "What was the Situation / Task?",
            "What Action did you take? What Result, with metrics?",
        ],
        "notes": "Use failure -> owning it -> concrete recovery -> lesson generalized.",
        "code": "",
    },
]

# Each entry: (item index, rating, days ago, reflection)
DEMO_ATTEMPTS: list[tuple[int, str, int, str]] = [
    (0, "good", 1, "immediate hash map: 2 min"),
    (1, "good", 14, "recursive query still slow; walk build again"),
    (2, "easy", 20, ""),
    (3, "hard", 2, "moved shared_ptr -> unique_ptr manually; felt shaky"),
    (4, "good", 3, "drew the door/prize tree"),
    (5, "hard", 8, "cache sizing fuzzy; revisit"),
]