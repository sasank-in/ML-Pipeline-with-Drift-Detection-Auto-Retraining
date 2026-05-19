"""Shared HTML scaffolding for service UIs.

Each service passes a small `palette` dict to theme the same base CSS.
Removes ~80 lines of duplicated style across ingestion + prediction services.
"""
from markupsafe import escape


DEFAULT_PALETTE = {
    "accent": "#00c2b3",      # primary accent
    "accent_alt": "#3a86ff",  # gradient companion
    "bg_glow": "#dff7f2",     # radial gradient highlight
    "nav_a": "#101827",       # nav gradient start
    "nav_b": "#1d2d44",       # nav gradient mid
}


def base_style(palette: dict = None) -> str:
    p = {**DEFAULT_PALETTE, **(palette or {})}
    return f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=IBM+Plex+Mono&display=swap');
    :root {{
        --ink: #0b1220;
        --paper: #f7f4ef;
        --accent: {p['accent']};
        --accent-alt: {p['accent_alt']};
        --coral: #ff6b6b;
        --slate: #223249;
        --glass: rgba(255, 255, 255, 0.72);
        --shadow: 0 20px 40px rgba(12, 17, 29, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: 'Space Grotesk', sans-serif; margin: 0; background: radial-gradient(1200px 600px at 10% -10%, {p['bg_glow']} 0%, #f7f4ef 45%, #f3efe7 100%); color: var(--ink); }}
    .nav {{ background: linear-gradient(120deg, {p['nav_a']} 0%, {p['nav_b']} 60%, #0b1220 100%); padding: 16px 40px; position: sticky; top: 0; z-index: 10; }}
    .nav a {{ color: white; text-decoration: none; margin-right: 12px; padding: 10px 16px; border-radius: 999px; font-weight: 600; letter-spacing: 0.2px; transition: all 0.2s ease; }}
    .nav a:hover {{ background: rgba(255,255,255,0.12); transform: translateY(-1px); }}
    .nav a.active {{ background: linear-gradient(135deg, var(--accent), var(--accent-alt)); }}
    .container {{ max-width: 980px; margin: 28px auto; background: var(--glass); backdrop-filter: blur(8px); padding: 32px; border-radius: 18px; box-shadow: var(--shadow); border: 1px solid rgba(12, 17, 29, 0.06); animation: fadeUp 0.6s ease both; }}
    h1 {{ color: var(--ink); border-bottom: 3px solid var(--accent); padding-bottom: 10px; margin-top: 0; font-size: 28px; letter-spacing: 0.3px; }}
    .status {{ background: linear-gradient(120deg, #1dd3b0, #06d6a0); color: #042019; padding: 6px 16px; border-radius: 999px; display: inline-block; font-weight: 700; }}
    .status.warning {{ background: linear-gradient(120deg, #f43f5e, #fb7185); color: #1f0a0a; }}
    .stats {{ display: flex; gap: 18px; margin: 22px 0; }}
    .stat-box {{ background: #101827; color: white; padding: 20px; border-radius: 16px; text-align: left; flex: 1; box-shadow: 0 12px 24px rgba(16, 24, 39, 0.18); animation: glowIn 0.6s ease both; }}
    .stat-box h3 {{ margin: 0; font-size: 13px; text-transform: uppercase; letter-spacing: 1.2px; opacity: 0.7; }}
    .stat-box p {{ margin: 10px 0 0 0; font-size: 28px; font-weight: 700; }}
    .stat-box.alt {{ background: linear-gradient(135deg, #003049, #1f6f8b); }}
    .form-group {{ margin: 16px 0; }}
    .form-group label {{ display: block; margin-bottom: 6px; font-weight: 600; color: var(--slate); }}
    textarea, input {{ width: 100%; padding: 12px; border: 1px solid rgba(12, 17, 29, 0.12); border-radius: 12px; font-family: 'IBM Plex Mono', monospace; background: white; }}
    textarea {{ height: 140px; }}
    button {{ background: linear-gradient(135deg, var(--accent), var(--accent-alt)); color: white; border: none; padding: 12px 24px; border-radius: 12px; cursor: pointer; font-size: 14px; font-weight: 700; letter-spacing: 0.3px; box-shadow: 0 10px 20px rgba(0, 194, 179, 0.2); transition: transform 0.2s ease, box-shadow 0.2s ease; }}
    button:hover {{ transform: translateY(-2px); box-shadow: 0 16px 28px rgba(0, 194, 179, 0.3); }}
    .result {{ background: #0b1220; color: #c7f9cc; padding: 16px; border-radius: 12px; margin-top: 15px; font-family: 'IBM Plex Mono', monospace; white-space: pre-wrap; }}
    .error {{ color: var(--coral); }}
    .success {{ color: #1dd3b0; }}
    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
    th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid rgba(12, 17, 29, 0.08); }}
    th {{ background: #101827; color: white; border-radius: 8px; }}
    tr:hover {{ background: rgba(0, 194, 179, 0.08); }}
    .model-info {{ background: linear-gradient(135deg, #111827, #1f2937); color: white; padding: 20px; border-radius: 14px; margin: 20px 0; box-shadow: 0 12px 24px rgba(16, 24, 39, 0.18); }}
    .prediction-result {{ background: linear-gradient(135deg, #10b981, #22d3ee); color: #052316; padding: 20px; border-radius: 14px; margin: 20px 0; }}
    .prediction-result h3 {{ margin-top: 0; }}
    @keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    @keyframes glowIn {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    @media (max-width: 900px) {{ .stats {{ flex-direction: column; }} .nav {{ padding: 12px 18px; }} .container {{ margin: 18px; }} }}
</style>
"""


def nav_html(links: list, active: str = "") -> str:
    """Build the nav bar.

    links: list of (href, label) tuples.
    active: href value to mark as active.
    """
    parts = ['<div class="nav">']
    for href, label in links:
        cls = "active" if href == active else ""
        parts.append(f'<a href="{escape(href)}" class="{cls}">{escape(label)}</a>')
    parts.append('</div>')
    return "".join(parts)
