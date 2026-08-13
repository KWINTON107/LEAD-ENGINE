"""
Builds a single-file, responsive HTML preview site from real scraped data.
No fabricated info: every field either comes from scraped_data or is omitted.
The generated site clearly labels itself as an unsolicited concept preview
(not a live replacement) and does NOT reuse the business's actual logo file,
to stay clear of any copyright/trademark gray area — it uses a text wordmark
built from their brand colors instead.
"""
import html as html_lib
import re

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{business_name} — Concept Preview</title>
<style>
  :root {{
    --brand-primary: {color_primary};
    --brand-secondary: {color_secondary};
    --text: #1a1a1a;
    --bg: #ffffff;
    --muted: #6b7280;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, "Segoe UI", Roboto, sans-serif; color: var(--text); line-height: 1.6; }}
  .banner {{
    background: #111827; color: #fff; text-align: center; padding: 10px 16px;
    font-size: 0.85rem;
  }}
  .banner a {{ color: #93c5fd; }}
  header {{
    background: linear-gradient(135deg, var(--brand-primary), var(--brand-secondary));
    color: #fff; padding: 80px 24px; text-align: center;
  }}
  header h1 {{ font-size: clamp(1.8rem, 5vw, 3rem); margin-bottom: 16px; }}
  header p {{ font-size: 1.1rem; opacity: 0.95; max-width: 600px; margin: 0 auto; }}
  .cta {{
    display: inline-block; margin-top: 28px; padding: 14px 32px; background: #fff;
    color: var(--brand-primary); font-weight: 600; border-radius: 999px; text-decoration: none;
  }}
  section {{ padding: 60px 24px; max-width: 1000px; margin: 0 auto; }}
  h2 {{ font-size: 1.8rem; margin-bottom: 28px; text-align: center; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; }}
  .card {{
    border: 1px solid #e5e7eb; border-radius: 12px; padding: 24px; background: #fafafa;
  }}
  .about {{ text-align: center; color: var(--muted); max-width: 700px; margin: 0 auto; }}
  .contact {{ background: #f9fafb; text-align: center; }}
  .contact-details {{ margin-top: 20px; color: var(--muted); }}
  footer {{ text-align: center; padding: 30px; color: var(--muted); font-size: 0.85rem; }}
  @media (max-width: 600px) {{ section {{ padding: 40px 16px; }} }}
</style>
</head>
<body>
  <div class="banner">
    This is an unsolicited concept preview created by {sender_name} — not affiliated with {business_name}.
    <a href="mailto:{sender_email}">Questions / remove this? Contact {sender_name}</a>
  </div>

  <header>
    <h1>{business_name}</h1>
    <p>{tagline}</p>
    <a class="cta" href="#contact">Get in touch</a>
  </header>

  <section id="services">
    <h2>Services</h2>
    <div class="grid">
      {services_html}
    </div>
  </section>

  <section class="about">
    <h2>About</h2>
    <p>{about_text}</p>
  </section>

  <section class="contact" id="contact">
    <h2>Visit or Contact Us</h2>
    <div class="contact-details">
      {contact_html}
    </div>
  </section>

  <footer>
    Concept preview generated {generated_date} by {sender_name}. Original site:
    <a href="{original_url}">{original_url}</a>
  </footer>
</body>
</html>
"""


def _esc(s):
    return html_lib.escape(s or "")


def generate_site_html(scraped_data: dict, original_url: str, sender_name: str,
                        sender_email: str, generated_date: str) -> str:
    colors = scraped_data.get("brand_colors") or ["#2563eb", "#1e293b"]
    color_primary = colors[0] if re.match(r"^#[0-9a-fA-F]{3,6}$", colors[0]) else "#2563eb"
    color_secondary = colors[1] if len(colors) > 1 and re.match(r"^#[0-9a-fA-F]{3,6}$", colors[1]) else "#1e293b"

    services = scraped_data.get("services") or []
    if services:
        services_html = "\n".join(f'<div class="card">{_esc(s)}</div>' for s in services)
    else:
        services_html = '<div class="card">Services list not found on original site.</div>'

    contact_bits = []
    if scraped_data.get("phones"):
        contact_bits.append(f"Phone: {_esc(scraped_data['phones'][0])}")
    if scraped_data.get("emails"):
        contact_bits.append(f"Email: {_esc(scraped_data['emails'][0])}")
    contact_html = "<br>".join(contact_bits) or "Contact details not found on original site."

    about_text = _esc((scraped_data.get("about_text") or "")[:400]) or "No about text found on original site."

    return TEMPLATE.format(
        business_name=_esc(scraped_data.get("business_name", "")),
        tagline="A modern take on your online presence",
        sender_name=_esc(sender_name),
        sender_email=_esc(sender_email),
        services_html=services_html,
        about_text=about_text,
        contact_html=contact_html,
        generated_date=_esc(generated_date),
        original_url=_esc(original_url),
        color_primary=color_primary,
        color_secondary=color_secondary,
    )
