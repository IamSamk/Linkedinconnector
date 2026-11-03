import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DB_PATH = os.getenv("DATABASE_PATH", "./osint_discovery.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            slug TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            headline TEXT,
            location TEXT,
            profile_url TEXT NOT NULL,
            summary TEXT,
            experiences_json TEXT DEFAULT '[]',
            educations_json TEXT DEFAULT '[]',
            skills_json TEXT DEFAULT '[]',
            source_method TEXT,
            batch_tag TEXT,
            discovered_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS public_jobs (
            job_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,
            work_type TEXT,
            posted_ago TEXT,
            job_url TEXT NOT NULL,
            department_tag TEXT,
            discovered_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def upsert_profile(profile: Dict[str, Any]) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    slug = profile["slug"]
    default_url = f"https://www.linkedin.com/in/{slug}"
    cursor.execute(
        """
        INSERT INTO profiles (
            slug, full_name, headline, location, profile_url,
            summary, experiences_json, educations_json, skills_json,
            source_method, batch_tag, discovered_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
            full_name=excluded.full_name,
            headline=excluded.headline,
            location=excluded.location,
            summary=excluded.summary,
            experiences_json=excluded.experiences_json,
            educations_json=excluded.educations_json,
            skills_json=excluded.skills_json,
            source_method=excluded.source_method,
            batch_tag=excluded.batch_tag,
            discovered_at=excluded.discovered_at
        """,
        (
            slug,
            profile.get("full_name", "Unknown"),
            profile.get("headline", ""),
            profile.get("location", ""),
            profile.get("profile_url", default_url),
            profile.get("summary", ""),
            json.dumps(profile.get("experiences", [])),
            json.dumps(profile.get("educations", [])),
            json.dumps(profile.get("skills", [])),
            profile.get("source_method", "xray_serp"),
            profile.get("batch_tag", ""),
            now,
        ),
    )
    conn.commit()
    conn.close()


def list_profiles(batch_tag: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if batch_tag:
        cursor.execute(
            "SELECT * FROM profiles WHERE batch_tag = ? ORDER BY discovered_at DESC",
            (batch_tag,),
        )
    else:
        cursor.execute("SELECT * FROM profiles ORDER BY discovered_at DESC")
    rows = cursor.fetchall()
    conn.close()
    results: List[Dict[str, Any]] = []
    for r in rows:
        results.append(
            {
                "slug": r["slug"],
                "full_name": r["full_name"],
                "headline": r["headline"],
                "location": r["location"],
                "profile_url": r["profile_url"],
                "summary": r["summary"],
                "experiences": json.loads(r["experiences_json"] or "[]"),
                "educations": json.loads(r["educations_json"] or "[]"),
                "skills": json.loads(r["skills_json"] or "[]"),
                "source_method": r["source_method"],
                "batch_tag": r["batch_tag"],
                "discovered_at": r["discovered_at"],
            }
        )
    return results


def get_profile_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles WHERE slug = ?", (slug,))
    r = cursor.fetchone()
    conn.close()
    if not r:
        return None
    return {
        "slug": r["slug"],
        "full_name": r["full_name"],
        "headline": r["headline"],
        "location": r["location"],
        "profile_url": r["profile_url"],
        "summary": r["summary"],
        "experiences": json.loads(r["experiences_json"] or "[]"),
        "educations": json.loads(r["educations_json"] or "[]"),
        "skills": json.loads(r["skills_json"] or "[]"),
        "source_method": r["source_method"],
        "batch_tag": r["batch_tag"],
        "discovered_at": r["discovered_at"],
    }


def upsert_job(job: Dict[str, Any]) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        """
        INSERT INTO public_jobs (
            job_id, title, company, location, work_type,
            posted_ago, job_url, department_tag, discovered_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
            title=excluded.title,
            company=excluded.company,
            location=excluded.location,
            posted_ago=excluded.posted_ago,
            discovered_at=excluded.discovered_at
        """,
        (
            job["job_id"],
            job["title"],
            job["company"],
            job.get("location", ""),
            job.get("work_type", ""),
            job.get("posted_ago", ""),
            job["job_url"],
            job.get("department_tag", "General"),
            now,
        ),
    )
    conn.commit()
    conn.close()


def list_jobs(limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM public_jobs ORDER BY discovered_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
