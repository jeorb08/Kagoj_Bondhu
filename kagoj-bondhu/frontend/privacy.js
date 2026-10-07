/* Browser-level consent for the existing prototype.
   This is not server-side consent enforcement. */
(() => {
  const originalFetch = window.fetch.bind(window);
  let consentGiven = false;

  window.fetch = async function (input, init) {
    const url = new URL(
      input instanceof Request ? input.url : String(input),
      location.href
    );

    const routes = new Set([
      "/api/read",
      "/api/verify/read",
      "/api/check",
      "/api/verify",
      "/api/speak"
    ]);

    const method = (
      init?.method ||
      (input instanceof Request ? input.method : "GET")
    ).toUpperCase();

    if (
      url.origin === location.origin &&
      method === "POST" &&
      routes.has(url.pathname) &&
      !consentGiven
    ) {
      const message = [
        "Cloud processing permission / ক্লাউডে তথ্য পাঠানোর অনুমতি",
        "",
        "Documents or extracted details may be sent to the configured AI provider; spoken text may be sent to the speech provider.",
        "কাগজ বা কাগজের তথ্য নির্ধারিত এআই সেবায় এবং অডিওর লেখা ভয়েস সেবায় যেতে পারে।",
        "",
        "Use synthetic or properly redacted documents for this demo. Provider retention follows its own settings and terms.",
        "ডেমোতে কৃত্রিম বা ব্যক্তিগত তথ্য ঢাকা কাগজ ব্যবহার করুন।",
        "",
        "Allow processing during this page session? Cancel to decline.",
        "এই পেজ সেশনে অনুমতি দেবেন? না চাইলে Cancel চাপুন।"
      ].join("\n");

      if (!window.confirm(message)) {
        return new Response(JSON.stringify({
          detail: "Cloud processing cancelled: permission was not given."
        }), {
          status: 403,
          headers: { "Content-Type": "application/json" }
        });
      }

      consentGiven = true;
    }

    return originalFetch(input, init);
  };
})();