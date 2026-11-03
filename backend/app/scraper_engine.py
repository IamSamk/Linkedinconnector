import asyncio
import json
import os
import random
import re
import urllib.parse
from typing import Any, Dict, List, Optional

import certifi
import httpx
from bs4 import BeautifulSoup

# Corrected LinkedIn Guest API parameter maps
WORK_TYPE_MAP = {
    "1": "On-site",
    "2": "Remote",   # LinkedIn's actual API maps 2=Remote, 3=Hybrid
    "3": "Hybrid",
}

EXPERIENCE_LEVEL_MAP = {
    "1": "Internship",
    "2": "Entry Level",
    "3": "Associate",
    "4": "Mid-Senior",
    "5": "Director",
    "6": "Executive",
}


def build_cohort_xray_query(
    institution: str,
    batch_year: str,
    role_keywords: List[str],
    location: Optional[str] = None,
) -> str:
    """Builds a Boolean X-Ray query for zero-account-risk cohort shortlisting."""
    inst_clause = f'("{institution}")'
    year_int = int(batch_year) if batch_year.isdigit() else None
    if year_int:
        year_clause = f'("{year_int - 4} - {year_int}" OR "{year_int - 3} - {year_int}" OR "{batch_year}")'
    else:
        year_clause = f'"{batch_year}"'

    cleaned_roles = [f'"{kw.strip()}"' for kw in role_keywords if kw.strip()]
    role_clause = f"({' OR '.join(cleaned_roles)})" if cleaned_roles else ""

    loc_clause = f'"{location.strip()}"' if location and location.strip() else ""
    parts = ["site:linkedin.com/in/", inst_clause, year_clause]
    if role_clause:
        parts.append(role_clause)
    if loc_clause:
        parts.append(loc_clause)
    return " ".join(parts)


def extract_slug_from_url(url: str) -> Optional[str]:
    match = re.search(r"linkedin\.com/in/([a-zA-Z0-9\-_%]+)", url)
    if match:
        return urllib.parse.unquote(match.group(1)).strip("/")
    return None


async def serper_xray_search(query: str, num_results: int = 10) -> List[Dict[str, str]]:
    """Executes an off-platform X-Ray query using Serper.dev or falls back to DuckDuckGo HTML."""
    serper_key = os.getenv("SERPER_API_KEY", "").strip()
    results: List[Dict[str, str]] = []

    async with httpx.AsyncClient(verify=certifi.where(), timeout=15.0) as client:
        if serper_key:
            resp = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
                json={"q": query, "num": num_results},
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("organic", []):
                    link = item.get("link", "")
                    slug = extract_slug_from_url(link)
                    if slug:
                        results.append(
                            {
                                "slug": slug,
                                "title": item.get("title", ""),
                                "snippet": item.get("snippet", ""),
                                "url": f"https://www.linkedin.com/in/{slug}",
                            }
                        )
                return results

        # Fallback: Unauthenticated DuckDuckGo Lite HTML search
        ddg_url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            "Referer": "https://duckduckgo.com/",
        }
        try:
            resp = await client.post(ddg_url, data={"q": query}, headers=headers)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for a_tag in soup.select("a.result__a"):
                    href = a_tag.get("href", "")
                    slug = extract_slug_from_url(href)
                    if slug:
                        parent = a_tag.find_parent("div", class_="result__body")
                        snippet_el = parent.select_one(".result__snippet") if parent else None
                        results.append(
                            {
                                "slug": slug,
                                "title": a_tag.get_text(strip=True),
                                "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                                "url": f"https://www.linkedin.com/in/{slug}",
                            }
                        )
        except Exception:
            pass

    return results


def parse_public_profile_html(
    html: str,
    slug: str,
    fallback_title: str = "",
    fallback_snippet: str = "",
) -> Dict[str, Any]:
    """
    Extracts structured CV data from a public LinkedIn profile's <script type="application/ld+json">
    and OpenGraph meta tags.
    """
    soup = BeautifulSoup(html, "html.parser")
    profile_data: Dict[str, Any] = {
        "slug": slug,
        "full_name": fallback_title.split("-")[0].split("|")[0].strip() if fallback_title else slug,
        "headline": fallback_title.split("-")[1].strip() if "-" in fallback_title else fallback_snippet,
        "location": "",
        "profile_url": f"https://www.linkedin.com/in/{slug}",
        "summary": fallback_snippet,
        "experiences": [],
        "educations": [],
        "skills": [],
        "source_method": "incognito_ld_json",
    }

    ld_scripts = soup.find_all("script", {"type": "application/ld+json"})
    for script in ld_scripts:
        try:
            raw_json = json.loads(script.string or "{}")
            graph = raw_json.get("@graph", [raw_json]) if isinstance(raw_json, dict) else raw_json
            for node in graph:
                if not isinstance(node, dict):
                    continue
                if node.get("@type") == "Person":
                    profile_data["full_name"] = node.get("name") or profile_data["full_name"]
                    job_titles = node.get("jobTitle")
                    if isinstance(job_titles, list) and job_titles:
                        profile_data["headline"] = " | ".join(str(j) for j in job_titles)
                    elif isinstance(job_titles, str) and job_titles:
                        profile_data["headline"] = job_titles

                    address = node.get("address", {})
                    if isinstance(address, dict):
                        profile_data["location"] = address.get("addressLocality", "")

                    if node.get("description"):
                        profile_data["summary"] = node["description"]

                    works_for = node.get("worksFor", [])
                    if isinstance(works_for, dict):
                        works_for = [works_for]
                    for org in works_for:
                        if isinstance(org, dict):
                            member_role = org.get("member", {}) if isinstance(org.get("member"), dict) else {}
                            profile_data["experiences"].append(
                                {
                                    "company": org.get("name", "Organization"),
                                    "title": member_role.get("roleName", profile_data["headline"]),
                                    "start_date": member_role.get("startDate", ""),
                                    "end_date": member_role.get("endDate", "Present"),
                                    "description": member_role.get("description", ""),
                                }
                            )

                    alumni_of = node.get("alumniOf", [])
                    if isinstance(alumni_of, dict):
                        alumni_of = [alumni_of]
                    for edu in alumni_of:
                        if isinstance(edu, dict):
                            member_info = edu.get("member", {}) if isinstance(edu.get("member"), dict) else {}
                            profile_data["educations"].append(
                                {
                                    "school": edu.get("name", "University"),
                                    "degree": member_info.get("roleName", ""),
                                    "start_date": member_info.get("startDate", ""),
                                    "end_date": member_info.get("endDate", ""),
                                }
                            )
        except Exception:
            continue

    og_title = soup.find("meta", {"property": "og:title"})
    og_desc = soup.find("meta", {"property": "og:description"})
    if og_title and og_title.get("content"):
        title_parts = og_title["content"].split(" - ")
        if title_parts:
            profile_data["full_name"] = title_parts[0].strip()
        if len(title_parts) > 1 and not profile_data["headline"]:
            profile_data["headline"] = title_parts[1].replace("| LinkedIn", "").strip()
    if og_desc and og_desc.get("content") and not profile_data["summary"]:
        profile_data["summary"] = og_desc["content"].strip()

    return profile_data


async def fetch_incognito_profile_cv(
    slug: str,
    fallback_title: str = "",
    fallback_snippet: str = "",
    jitter_min: float = 1.2,
    jitter_max: float = 3.0,
) -> Dict[str, Any]:
    """
    Fetches a public profile in a clean cookie-less context with a Google Referer header.
    Falls back to X-Ray SERP metadata if an authwall redirect is encountered.
    """
    await asyncio.sleep(random.uniform(jitter_min, jitter_max))
    url = f"https://www.linkedin.com/in/{slug}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Cache-Control": "no-cache",
    }

    async with httpx.AsyncClient(verify=certifi.where(), follow_redirects=False, timeout=15.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200 and "authwall" not in str(resp.url):
                return parse_public_profile_html(resp.text, slug, fallback_title, fallback_snippet)
        except Exception:
            pass

    clean_name = fallback_title.split("-")[0].split("|")[0].strip() if fallback_title else slug
    headline = ""
    if "-" in fallback_title:
        headline = " - ".join(fallback_title.split("-")[1:]).replace("| LinkedIn", "").strip()
    return {
        "slug": slug,
        "full_name": clean_name,
        "headline": headline or fallback_snippet[:140],
        "location": "",
        "profile_url": url,
        "summary": fallback_snippet,
        "experiences": [],
        "educations": [],
        "skills": [],
        "source_method": "xray_snippet_fallback",
    }


def parse_voyager_normalized_json(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parses exported normalized JSON (`application/vnd.linkedin.normalized+json+2.1`)
    from HAR files or DevTools network captures.
    """
    included = payload.get("included", [])
    if not isinstance(included, list):
        return []

    profiles_by_urn: Dict[str, Dict[str, Any]] = {}
    positions_by_profile: Dict[str, List[Dict[str, Any]]] = {}
    educations_by_profile: Dict[str, List[Dict[str, Any]]] = {}
    skills_by_profile: Dict[str, List[str]] = {}

    for entity in included:
        if not isinstance(entity, dict):
            continue
        etype = entity.get("$type", "")
        entity_urn = entity.get("entityUrn", "")

        if "Profile" in etype and entity.get("publicIdentifier"):
            slug = entity["publicIdentifier"]
            first_name = entity.get("firstName", "")
            last_name = entity.get("lastName", "")
            profiles_by_urn[entity_urn] = {
                "slug": slug,
                "full_name": f"{first_name} {last_name}".strip() or slug,
                "headline": entity.get("headline", ""),
                "location": entity.get("locationName", "") or entity.get("geoLocationName", ""),
                "profile_url": f"https://www.linkedin.com/in/{slug}",
                "summary": entity.get("summary", ""),
                "experiences": [],
                "educations": [],
                "skills": [],
                "source_method": "voyager_har_json",
            }
        elif "Position" in etype and entity.get("title"):
            prof_urn = entity.get("*profile") or entity_urn.rsplit(",", 1)[0]
            positions_by_profile.setdefault(prof_urn, []).append(
                {
                    "company": entity.get("companyName", ""),
                    "title": entity.get("title", ""),
                    "start_date": "",
                    "end_date": "",
                    "description": entity.get("description", ""),
                }
            )
        elif "Education" in etype and entity.get("schoolName"):
            prof_urn = entity.get("*profile") or entity_urn.rsplit(",", 1)[0]
            educations_by_profile.setdefault(prof_urn, []).append(
                {
                    "school": entity.get("schoolName", ""),
                    "degree": entity.get("degreeName", ""),
                    "start_date": "",
                    "end_date": "",
                }
            )
        elif "Skill" in etype and entity.get("name"):
            prof_urn = entity.get("*profile") or entity_urn.rsplit(",", 1)[0]
            skills_by_profile.setdefault(prof_urn, []).append(entity["name"])

    results = []
    for urn, prof in profiles_by_urn.items():
        prof["experiences"] = positions_by_profile.get(urn, [])
        prof["educations"] = educations_by_profile.get(urn, [])
        prof["skills"] = skills_by_profile.get(urn, [])
        results.append(prof)
    return results


async def fetch_public_guest_jobs(
    keywords: str,
    location: str = "India",
    f_WT: Optional[str] = None,
    f_TPR: Optional[str] = "r86400",
    f_E: Optional[str] = None,
    start: int = 0,
) -> List[Dict[str, Any]]:
    """
    Scrapes LinkedIn's unauthenticated /jobs-guest/jobs/api/seeMoreJobPostings/search endpoint.
    """
    params: Dict[str, Any] = {
        "keywords": keywords,
        "location": location,
        "start": start,
    }
    if f_WT in WORK_TYPE_MAP:
        params["f_WT"] = f_WT
    if f_TPR:
        params["f_TPR"] = f_TPR
    if f_E:
        params["f_E"] = f_E

    url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }

    jobs: List[Dict[str, Any]] = []
    async with httpx.AsyncClient(verify=certifi.where(), timeout=15.0) as client:
        try:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for li in soup.find_all("li"):
                    card = li.find("div", class_="base-card")
                    if not card:
                        continue
                    entity_urn = card.get("data-entity-urn", "")
                    job_id = entity_urn.split(":")[-1] if ":" in entity_urn else str(random.randint(100000, 999999))
                    title_el = li.find("h3", class_="base-search-card__title")
                    company_el = li.find("h4", class_="base-search-card__subtitle")
                    loc_el = li.find("span", class_="job-search-card__location")
                    time_el = li.find("time")
                    link_el = li.find("a", class_="base-card__full-link")

                    jobs.append(
                        {
                            "job_id": job_id,
                            "title": title_el.get_text(strip=True) if title_el else "Unknown Role",
                            "company": company_el.get_text(strip=True) if company_el else "Unknown Company",
                            "location": loc_el.get_text(strip=True) if loc_el else location,
                            "work_type": WORK_TYPE_MAP.get(f_WT or "", "Unspecified"),
                            "posted_ago": time_el.get_text(strip=True) if time_el else "Recently",
                            "job_url": (
                                link_el.get("href", "").split("?")[0]
                                if link_el
                                else f"https://www.linkedin.com/jobs/view/{job_id}"
                            ),
                            "department_tag": classify_department(
                                title_el.get_text(strip=True) if title_el else keywords
                            ),
                        }
                    )
        except Exception:
            pass
    return jobs


async def resolve_public_typeahead(query: str, kind: str = "GEO") -> List[Dict[str, Any]]:
    """Queries LinkedIn's unauthenticated /jobs-guest/api/typeaheadHits endpoint."""
    url = "https://www.linkedin.com/jobs-guest/api/typeaheadHits"
    params: Dict[str, str] = {"query": query}
    if kind.upper() == "COMPANY":
        params["typeaheadType"] = "COMPANY"
    else:
        params["origin"] = "jserp"
        params["typeaheadType"] = "GEO"
        params["geoTypes"] = "POPULATED_PLACE,ADMIN_DIVISION_1,COUNTRY_REGION"

    async with httpx.AsyncClient(verify=certifi.where(), timeout=10.0) as client:
        try:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
    return []


def classify_department(title: str) -> str:
    t = title.lower()
    if any(
        k in t
        for k in ["software", "ai", "ml", "data", "cloud", "full stack", "backend", "frontend", "cyber", "devops"]
    ):
        return "SoCSE (Computer Science & Engineering)"
    if any(k in t for k in ["design", "ux", "ui", "product design", "graphic"]):
        return "School of Design"
    if any(k in t for k in ["finance", "marketing", "business", "gtm", "sales", "operations"]):
        return "School of Business"
    return "General / Interdisciplinary"


def render_profile_markdown_cv(profile: Dict[str, Any]) -> str:
    lines = [
        f"# {profile.get('full_name', profile['slug'])}",
        f"**Headline:** {profile.get('headline', 'N/A')}  ",
        f"**Location:** {profile.get('location') or 'Unspecified'}  ",
        f"**LinkedIn URL:** {profile.get('profile_url')}  ",
        f"**Extraction Source:** `{profile.get('source_method', 'N/A')}`",
        "",
        "## Summary",
        profile.get("summary") or "_No summary text available in public snapshot._",
        "",
        "## Experience",
    ]
    experiences = profile.get("experiences", [])
    if experiences:
        for exp in experiences:
            lines.append(f"### {exp.get('title', 'Role')} — {exp.get('company', 'Organization')}")
            if exp.get("start_date") or exp.get("end_date"):
                lines.append(f"*{exp.get('start_date', '')} - {exp.get('end_date', 'Present')}*")
            if exp.get("description"):
                lines.append(f"{exp['description']}")
            lines.append("")
    else:
        lines.append("_No structured experience entries exposed in guest snapshot._")
        lines.append("")

    lines.append("## Education")
    educations = profile.get("educations", [])
    if educations:
        for edu in educations:
            lines.append(
                f"- **{edu.get('school', 'Institution')}** — {edu.get('degree', '')} "
                f"({edu.get('start_date', '')} - {edu.get('end_date', '')})"
            )
    else:
        lines.append("_No structured education entries exposed in guest snapshot._")

    if profile.get("skills"):
        lines.append("")
        lines.append("## Skills")
        lines.append(", ".join(profile["skills"]))

    return "\n".join(lines)
