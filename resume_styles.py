"""Shared print and preview style definitions."""
RESUME_STYLES = {
    'Word Template': dict(css='word', font='NotoSerif', margin=19, leading=4.6, name_size=23, compact=False, accent=None, rules=True, centered=False),
    'Classic Professional': dict(css='classic', font='NotoSerif', margin=19, leading=4.6, name_size=23, compact=False, accent=None, rules=True, centered=False),
    'Modern Minimal': dict(css='modern', font='NotoSans', margin=19, leading=4.6, name_size=23, compact=False, accent=(164,68,37), rules=True, centered=False),
    'Technical Resume': dict(css='technical', font='NotoSans', margin=16, leading=4.2, name_size=21, compact=True, accent=None, rules=True, centered=False),
    'Editorial': dict(css='editorial', font='NotoSerif', margin=20, leading=4.7, name_size=26, compact=False, accent=(39,62,78), rules=False, centered=True),
    'Compact Professional': dict(css='compact', font='NotoSans', margin=16, leading=4.0, name_size=20, compact=True, accent=None, rules=True, centered=False),
}

STYLE_DESCRIPTIONS = {
    'Word Template': 'The supplied two-column Word layout, adapted to your resume sections.',
    'Classic Professional': 'Traditional serif typography and clear section rules.',
    'Modern Minimal': 'Clean sans-serif text with a restrained terracotta accent.',
    'Technical Resume': 'Compact technical layout with skills and projects first.',
    'Editorial': 'A centered serif name, quiet navy headings, and open section spacing.',
    'Compact Professional': 'A tighter single-column layout for a longer career history.',
}
