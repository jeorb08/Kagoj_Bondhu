/* Proposed upay journey. All wallet transactions below are fictional. */
(() => {
  const credits = [
    { id: "DEMO-001", label: "Salary credit A", amount: 16000 },
    { id: "DEMO-002", label: "Salary credit B / second payment", amount: 950 }
  ];

  const money = n => new Intl.NumberFormat("en-BD", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(n);

  window.walletPanel = function () {
    if (vs.module !== "payslip" || !vs.confirmed) return "";

    const raw = vs.values.net;
    if (raw === "" || raw == null) return "";

    const net = Number(raw);
    if (!Number.isFinite(net) || net < 0) return "";

    return `
      <section class="box" style="margin-top:24px">
        <h3>${L(
          "Compare salary with wallet credits",
          "ওয়ালেটে পাওয়া টাকার সঙ্গে বেতন মিলিয়ে দেখুন"
        )}</h3>

        <p class="fine">${L(
          "Proposed upay integration demo. Fictional transactions; no account is connected.",
          "প্রস্তাবিত upay সংযোগের ডেমো। লেনদেনগুলো কাল্পনিক; কোনো অ্যাকাউন্ট যুক্ত নেই।"
        )}</p>

        <p>${L("Confirmed printed net pay", "নিশ্চিত করা ছাপানো নিট বেতন")}:
          <strong>৳${money(net)}</strong>
        </p>

        <p>${L(
          "Select credits belonging to this salary period. You may select multiple payments.",
          "এই বেতনের সময়কালের টাকা নির্বাচন করুন। একাধিক পেমেন্ট নির্বাচন করা যাবে।"
        )}</p>

        ${credits.map(t => `
          <label style="display:block;padding:12px 0">
            <input type="checkbox" data-wallet-credit="${t.id}">
            ${t.id} · ${t.label} · ৳${money(t.amount)}
          </label>
        `).join("")}

        <label style="display:block;margin:12px 0">
          <input type="checkbox" id="wallet-period-confirm">
          ${L(
            "For this demo, I confirm these credits belong to the same salary period.",
            "এই ডেমোতে নির্বাচিত টাকা একই বেতনের সময়কালের বলে নিশ্চিত করছি।"
          )}
        </label>

        <button type="button" class="btn primary" id="wallet-compare">
          ${L("Compare amounts", "টাকার পরিমাণ মিলিয়ে দেখুন")}
        </button>

        <div id="wallet-result" role="status" aria-live="polite"></div>
      </section>
    `;
  };

  // Remove old results whenever the selection changes.
  document.addEventListener("change", e => {
    if (e.target.matches(
      "[data-wallet-credit], #wallet-period-confirm"
    )) {
      document.getElementById("wallet-result")?.replaceChildren();
    }
  });

  document.addEventListener("click", e => {
    if (!e.target.closest("#wallet-compare")) return;

    const out = document.getElementById("wallet-result");
    if (!out) return;

    if (vs.module !== "payslip" || !vs.confirmed) {
      out.textContent = L(
        "Confirm the payslip fields first.",
        "আগে পে-স্লিপের তথ্য নিশ্চিত করুন।"
      );
      return;
    }

    const chosen = [...document.querySelectorAll(
      "[data-wallet-credit]:checked"
    )].map(el => credits.find(t => t.id === el.dataset.walletCredit))
      .filter(Boolean);

    if (!chosen.length ||
        !document.getElementById("wallet-period-confirm")?.checked) {
      out.textContent = L(
        "Select at least one credit and confirm the salary period.",
        "অন্তত একটি পেমেন্ট নির্বাচন করে বেতনের সময়কাল নিশ্চিত করুন।"
      );
      return;
    }

    const raw = vs.values.net;
    const net = Number(raw);
    if (raw === "" || raw == null || !Number.isFinite(net) || net < 0) {
      out.textContent = "Please confirm a valid net-pay amount.";
      return;
    }

    // Calculate in paisa to avoid ordinary decimal rounding differences.
    const expected = Math.round(net * 100);
    const received = chosen.reduce(
      (sum, t) => sum + Math.round(t.amount * 100), 0
    );
    const difference = expected - received;
    const refs = chosen.map(t => t.id).join(", ");

    const heading = difference === 0
      ? L("Selected amounts match", "নির্বাচিত টাকার পরিমাণ মিলেছে")
      : L("Difference needs clarification", "পার্থক্যের ব্যাখ্যা প্রয়োজন");

    out.innerHTML = `
      <h4>${heading}</h4>
      <p>${L("Selected credits", "নির্বাচিত পেমেন্ট")}: ${refs}</p>
      <p>${L("Printed net pay", "ছাপানো নিট বেতন")}:
        ৳${money(expected / 100)}<br>
        ${L("Selected wallet total", "নির্বাচিত মোট টাকা")}:
        ৳${money(received / 100)}<br>
        ${L("Absolute difference", "পার্থক্যের পরিমাণ")}:
        ৳${money(Math.abs(difference) / 100)}
      </p>
      <p class="fine">${L(
        "This compares amounts only. It does not verify payment authenticity or establish underpayment. Timing, missing credits or adjustments may explain a difference.",
        "এটি শুধু টাকার পরিমাণের তুলনা। পেমেন্টের সত্যতা বা কম বেতন দেওয়ার প্রমাণ নয়। সময়, বাদ পড়া পেমেন্ট বা সমন্বয়ের কারণে পার্থক্য হতে পারে।"
      )}</p>
    `;

    if (difference !== 0) {
      const label = document.createElement("p");
      label.textContent = L(
        "Clarification draft — review and copy for your employer/payroll team. Nothing is sent.",
        "ব্যাখ্যা চাওয়ার খসড়া — যাচাই করে নিয়োগকর্তা বা বেতন বিভাগকে দিতে পারেন। কিছু পাঠানো হয়নি।"
      );

      const draft = document.createElement("textarea");
      draft.readOnly = true;
      draft.rows = 6;
      draft.style.cssText =
        "width:100%;box-sizing:border-box;padding:12px;font:inherit";
      draft.setAttribute("aria-label", "Salary clarification draft");
      draft.value =
        `[ডেমো — কাল্পনিক লেনদেন]\n` +
        `আমার পে-স্লিপে নিট বেতন ৳${money(expected / 100)}। ` +
        `নির্বাচিত ওয়ালেট পেমেন্টের মোট ৳${money(received / 100)}। ` +
        `পার্থক্য ৳${money(Math.abs(difference) / 100)}। ` +
        `এটি আংশিক পেমেন্ট, সময়ের পার্থক্য বা কোনো সমন্বয়ের কারণে হয়েছে কি না জানাবেন। ` +
        `রেফারেন্স: ${refs}।`;

      out.append(label, draft);
    }
  });
})();