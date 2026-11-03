"use client";

import React, { useState, useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Experience {
  company: string;
  title: string;
  start_date: string;
  end_date: string;
  description: string;
}

interface Education {
  school: string;
  degree: string;
  start_date: string;
  end_date: string;
}

interface Profile {
  slug: string;
  full_name: string;
  headline: string;
  location: string;
  profile_url: string;
  summary: string;
  experiences: Experience[];
  educations: Education[];
  skills: string[];
  source_method: string;
  batch_tag: string;
}

interface JobItem {
  job_id: string;
  title: string;
  company: string;
  location: string;
  work_type: string;
  posted_ago: string;
  job_url: string;
  department_tag: string;
}

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<"csv" | "cohort" | "jobs" | "voyager">("cohort");
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");

  const [institution, setInstitution] = useState("RV University");
  const [batchYear, setBatchYear] = useState("2022");
  const [roleKeywords, setRoleKeywords] = useState("Founder, Co-Founder, Entrepreneur, CEO");
  const [cohortLocation, setCohortLocation] = useState("Bengaluru");
  const [constructedQuery, setConstructedQuery] = useState("");
  const [googleSearchUrl, setGoogleSearchUrl] = useState("");

  const [csvFile, setCsvFile] = useState<File | null>(null);

  const [jobKeywords, setJobKeywords] = useState("Software Engineer Intern");
  const [jobLocation, setJobLocation] = useState("Bengaluru");
  const [workType, setWorkType] = useState("1");
  const [timePosted, setTimePosted] = useState("r86400");

  const [rawVoyagerJson, setRawVoyagerJson] = useState("");

  useEffect(() => {
    fetchSavedProfiles();
  }, []);

  async function fetchSavedProfiles() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/profiles`);
      if (res.ok) {
        const data = await res.json();
        setProfiles(data.profiles || []);
      }
    } catch {
      // Backend offline
    }
  }

  async function handleCohortSearch(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setStatusMsg("Running off-platform X-Ray discovery & incognito JSON-LD extraction...");
    try {
      const res = await fetch(`${API_BASE}/api/v1/cohort/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          institution,
          batch_year: batchYear,
          role_keywords: roleKeywords.split(",").map((k) => k.trim()),
          location: cohortLocation,
          fetch_cv_details: true,
        }),
      });
      const data = await res.json();
      setConstructedQuery(data.constructed_xray_query || "");
      setGoogleSearchUrl(data.google_search_url || "");
      await fetchSavedProfiles();
      setStatusMsg(`Discovered ${data.results_count || 0} matching cohort profiles.`);
    } catch (err) {
      setStatusMsg(`Error connecting to backend (${API_BASE}): ${String(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleCsvUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!csvFile) return;
    setLoading(true);
    setStatusMsg("Processing bulk CSV names via regulated off-platform slug resolution...");
    try {
      const formData = new FormData();
      formData.append("file", csvFile);
      const res = await fetch(`${API_BASE}/api/v1/csv/upload?fetch_cv_details=true`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      await fetchSavedProfiles();
      setStatusMsg(`Processed ${data.processed_count || 0} names from CSV.`);
    } catch (err) {
      setStatusMsg(`CSV Upload failed: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleJobSearch(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setStatusMsg("Querying unauthenticated /jobs-guest/ endpoint...");
    try {
      const res = await fetch(`${API_BASE}/api/v1/jobs/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          keywords: jobKeywords,
          location: jobLocation,
          f_WT: workType,
          f_TPR: timePosted,
          f_E: "1",
        }),
      });
      const data = await res.json();
      setJobs(data.jobs || []);
      setStatusMsg(`Fetched ${data.count || 0} public job postings.`);
    } catch (err) {
      setStatusMsg(`Job scrape error: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleVoyagerIngest(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const parsed = JSON.parse(rawVoyagerJson);
      const res = await fetch(`${API_BASE}/api/v1/ingest/voyager`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(parsed),
      });
      const data = await res.json();
      await fetchSavedProfiles();
      setStatusMsg(`Ingested ${data.ingested_count || 0} profiles from Voyager HAR JSON payload.`);
    } catch (err) {
      setStatusMsg(`Invalid JSON or ingest error: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <header className="flex flex-col md:flex-row md:items-center md:justify-between border-b border-slate-800 pb-6 mb-8 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white">
              LinkedIn Public OSINT & Cohort Discovery Suite
            </h1>
            <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Next.js 16.4.2 • FastAPI 0.162.0 • Uvicorn 0.54.0 • pnpm 12.17.0
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Zero-Account-Risk X-Ray Resolution • Incognito JSON-LD CV Parser • Corrected Guest Jobs API • HAR JSON Parser
          </p>
        </div>
        <div className="flex gap-3">
          <a
            href={`${API_BASE}/api/v1/export/csv`}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
          >
            Export All Profiles (.CSV)
          </a>
        </div>
      </header>

      <div className="flex flex-wrap gap-2 mb-6">
        {[
          { id: "cohort", label: "1. Cohort Shortlister (RVU / Alumni)" },
          { id: "csv", label: "2. Bulk CSV → LinkedIn CV" },
          { id: "jobs", label: "3. Public Jobs Guest API" },
          { id: "voyager", label: "4. Voyager HAR JSON Ingest" },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id as "csv" | "cohort" | "jobs" | "voyager")}
            className={`px-4 py-2.5 rounded-lg text-sm font-medium transition ${
              activeTab === t.id
                ? "bg-blue-600 text-white shadow-lg shadow-blue-600/20"
                : "bg-slate-900 text-slate-400 hover:bg-slate-800 border border-slate-800"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {statusMsg && (
        <div className="mb-6 p-4 rounded-lg bg-slate-900 border border-slate-800 text-sm text-blue-300 flex items-center justify-between">
          <span>{statusMsg}</span>
          {loading && <span className="animate-pulse text-xs text-amber-400">Working...</span>}
        </div>
      )}

      {activeTab === "cohort" && (
        <section className="p-6 rounded-xl bg-slate-900/70 border border-slate-800 mb-8">
          <h2 className="text-lg font-semibold text-white mb-2">
            Cohort & Alumni Shortlister (Boolean X-Ray + JSON-LD CV)
          </h2>
          <p className="text-sm text-slate-400 mb-4">
            Shortlist users matching a compulsory institution, graduation batch, and role keywords without triggering LinkedIn Commercial Use Limits.
          </p>
          <form onSubmit={handleCohortSearch} className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Compulsory Institution</label>
              <input
                value={institution}
                onChange={(e) => setInstitution(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-white"
                placeholder="RV University"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Graduation / Batch Year</label>
              <input
                value={batchYear}
                onChange={(e) => setBatchYear(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-white"
                placeholder="2022"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Role Keywords (comma-separated)</label>
              <input
                value={roleKeywords}
                onChange={(e) => setRoleKeywords(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-white"
                placeholder="Founder, Co-Founder, Entrepreneur"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Location Filter</label>
              <input
                value={cohortLocation}
                onChange={(e) => setCohortLocation(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-white"
                placeholder="Bengaluru"
              />
            </div>
            <div className="md:col-span-4 flex items-center gap-4 mt-2">
              <button
                type="submit"
                disabled={loading}
                className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition disabled:opacity-50"
              >
                Shortlist Cohort & Extract CVs
              </button>
              {constructedQuery && (
                <div className="text-xs text-slate-400 flex-1 truncate">
                  <span className="text-slate-500">X-Ray Query: </span>
                  <code className="text-emerald-400">{constructedQuery}</code>{" "}
                  {googleSearchUrl && (
                    <a
                      href={googleSearchUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="ml-2 text-blue-400 underline"
                    >
                      Open in Google ↗
                    </a>
                  )}
                </div>
              )}
            </div>
          </form>
        </section>
      )}

      {activeTab === "csv" && (
        <section className="p-6 rounded-xl bg-slate-900/70 border border-slate-800 mb-8">
          <h2 className="text-lg font-semibold text-white mb-2">
            Bulk CSV Name List → Structured LinkedIn CV
          </h2>
          <p className="text-sm text-slate-400 mb-4">
            Upload a CSV with columns <code className="text-slate-200">name,organization,location,batch</code>. Resolves slugs off-platform and extracts public CV details with jitter pacing.
          </p>
          <form onSubmit={handleCsvUpload} className="flex flex-wrap items-center gap-4">
            <input
              type="file"
              accept=".csv"
              onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
              className="text-sm text-slate-300 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-slate-800 file:text-slate-200 hover:file:bg-slate-700"
            />
            <button
              type="submit"
              disabled={!csvFile || loading}
              className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition disabled:opacity-50"
            >
              Process CSV & Extract CVs
            </button>
          </form>
        </section>
      )}

      {activeTab === "jobs" && (
        <section className="p-6 rounded-xl bg-slate-900/70 border border-slate-800 mb-8">
          <h2 className="text-lg font-semibold text-white mb-2">
            Unauthenticated Guest Jobs Harvester (Corrected f_WT Mapping)
          </h2>
          <form onSubmit={handleJobSearch} className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Keywords</label>
              <input
                value={jobKeywords}
                onChange={(e) => setJobKeywords(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-white"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Location</label>
              <input
                value={jobLocation}
                onChange={(e) => setJobLocation(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-white"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Work Type (Corrected f_WT)</label>
              <select
                value={workType}
                onChange={(e) => setWorkType(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-white"
              >
                <option value="1">1 = On-site</option>
                <option value="2">2 = Remote (Corrected)</option>
                <option value="3">3 = Hybrid (Corrected)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Posting Freshness (f_TPR)</label>
              <select
                value={timePosted}
                onChange={(e) => setTimePosted(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-white"
              >
                <option value="r3600">Past 1 Hour (r3600)</option>
                <option value="r14400">Past 4 Hours (r14400)</option>
                <option value="r86400">Past 24 Hours (r86400)</option>
                <option value="r604800">Past Week (r604800)</option>
              </select>
            </div>
            <div className="md:col-span-4">
              <button
                type="submit"
                disabled={loading}
                className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition"
              >
                Fetch Public Guest Jobs
              </button>
            </div>
          </form>

          {jobs.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {jobs.map((j) => (
                <div key={j.job_id} className="p-4 rounded-lg bg-slate-950 border border-slate-800">
                  <div className="flex justify-between items-start">
                    <h3 className="font-semibold text-white text-sm">{j.title}</h3>
                    <span className="text-xs px-2 py-0.5 rounded bg-blue-500/10 text-blue-400">
                      {j.work_type}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 mt-1">{j.company} • {j.location}</p>
                  <div className="flex justify-between items-center mt-3 text-xs text-slate-500">
                    <span>{j.department_tag} • {j.posted_ago}</span>
                    <a href={j.job_url} target="_blank" rel="noreferrer" className="text-blue-400 hover:underline">
                      View Listing ↗
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {activeTab === "voyager" && (
        <section className="p-6 rounded-xl bg-slate-900/70 border border-slate-800 mb-8">
          <h2 className="text-lg font-semibold text-white mb-2">
            Voyager Normalized HAR JSON Ingest (`application/vnd.linkedin.normalized+json+2.1`)
          </h2>
          <p className="text-sm text-slate-400 mb-4">
            Paste a raw JSON response copied from DevTools Network tab (<code className="text-slate-200">/voyager/api/identity/dash/profiles</code> or <code className="text-slate-200">/voyager/api/graphql</code>) to extract normalized profile entities.
          </p>
          <form onSubmit={handleVoyagerIngest}>
            <textarea
              rows={6}
              value={rawVoyagerJson}
              onChange={(e) => setRawVoyagerJson(e.target.value)}
              placeholder='{"data": {}, "included": [{"$type": "com.linkedin.voyager.dash.identity.profile.Profile", "publicIdentifier": "example-user", "firstName": "Aarav", "lastName": "Sharma", "headline": "Founder @ Stealth"}]}'
              className="w-full p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200 mb-3"
            />
            <button
              type="submit"
              disabled={!rawVoyagerJson.trim() || loading}
              className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition"
            >
              Parse & Save Normalized Entities
            </button>
          </form>
        </section>
      )}

      {activeTab !== "jobs" && (
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">
              Discovered Profiles & Extracted CVs ({profiles.length})
            </h2>
          </div>
          {profiles.length === 0 ? (
            <div className="p-8 rounded-xl bg-slate-900/40 border border-slate-800 text-center text-sm text-slate-500">
              No profiles stored yet. Run a Cohort Shortlist, upload a CSV, or ingest a Voyager HAR payload above.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {profiles.map((p) => (
                <div
                  key={p.slug}
                  className="p-5 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h3 className="font-semibold text-white text-base">{p.full_name}</h3>
                        <p className="text-xs text-blue-400 mt-0.5">{p.headline}</p>
                      </div>
                      <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {p.batch_tag || p.source_method}
                      </span>
                    </div>
                    {p.location && (
                      <p className="text-xs text-slate-400 mt-1">{p.location}</p>
                    )}
                    {p.summary && (
                      <p className="text-xs text-slate-300 mt-3 line-clamp-3">{p.summary}</p>
                    )}
                    {p.experiences?.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-slate-800/80">
                        <p className="text-[11px] uppercase tracking-wider text-slate-500 mb-1">
                          Experience
                        </p>
                        {p.experiences.slice(0, 2).map((exp, idx) => (
                          <p key={idx} className="text-xs text-slate-300">
                            • <span className="font-medium">{exp.title}</span> @ {exp.company}
                          </p>
                        ))}
                      </div>
                    )}
                    {p.educations?.length > 0 && (
                      <div className="mt-2">
                        <p className="text-[11px] uppercase tracking-wider text-slate-500 mb-1">
                          Education
                        </p>
                        {p.educations.slice(0, 2).map((edu, idx) => (
                          <p key={idx} className="text-xs text-slate-300">
                            • {edu.school} {edu.end_date ? `(${edu.end_date})` : ""}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-800 text-xs">
                    <a
                      href={p.profile_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-blue-400 hover:underline"
                    >
                      linkedin.com/in/{p.slug} ↗
                    </a>
                    <a
                      href={`${API_BASE}/api/v1/profiles/${p.slug}/cv-markdown`}
                      target="_blank"
                      rel="noreferrer"
                      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
                    >
                      Download CV (.md)
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
