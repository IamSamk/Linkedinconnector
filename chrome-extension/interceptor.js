/**
 * Passive Voyager API Response Forwarder
 * Zero outbound requests to LinkedIn: only reads responses already fetched by LinkedIn's SPA.
 */
(function () {
  const origFetch = window.fetch;
  window.fetch = async function (...args) {
    const response = await origFetch.apply(this, args);
    try {
      const url = typeof args[0] === "string" ? args[0] : args[0]?.url || "";
      if (url.includes("/voyager/api/identity/dash/profiles") || url.includes("/voyager/api/graphql")) {
        const clone = response.clone();
        clone.json().then((data) => {
          if (data && Array.isArray(data.included)) {
            origFetch("http://localhost:8000/api/v1/ingest/voyager", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(data),
            }).catch(() => {});
          }
        }).catch(() => {});
      }
    } catch (_) {}
    return response;
  };
})();
