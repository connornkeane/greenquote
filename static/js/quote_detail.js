(() => {
  const layout = document.querySelector("[data-quote-id]");
  if (!layout) return;
  const quoteId = layout.dataset.quoteId;

  const forecastBtn = document.getElementById("forecast-btn");
  const forecastDays = document.getElementById("forecast-days");
  const forecastError = document.getElementById("forecast-error");
  const forecastLocation = document.getElementById("forecast-location");
  const forecastRecommend = document.getElementById("forecast-recommend");
  const forecastDate = document.getElementById("forecast-date");

  const proposalBtn = document.getElementById("proposal-btn");
  const proposalText = document.getElementById("proposal-text");
  const proposalError = document.getElementById("proposal-error");
  const proposalEmpty = document.getElementById("proposal-empty");
  const copyBtn = document.getElementById("copy-btn");

  function busy(button, label) {
    button.dataset.label = button.textContent;
    button.textContent = label;
    button.disabled = true;
  }

  function done(button, label) {
    button.textContent = label || button.dataset.label;
    button.disabled = false;
  }

  function niceDate(iso) {
    const [y, m, d] = iso.split("-").map(Number);
    return new Date(y, m - 1, d).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
  }

  function dayCard(day, pick) {
    const card = document.createElement("div");
    card.className = `day day-${day.rating.toLowerCase()}${pick ? " day-pick" : ""}`;
    const parts = [
      ["day-name", day.weekday],
      ["day-summary", day.summary],
      ["day-temp", `${day.high_f}° / ${day.low_f}°`],
      ["day-rain", `${day.rain_chance}% rain`],
      ["day-rating", day.rating],
    ];
    parts.forEach(([cls, text]) => {
      const span = document.createElement("span");
      span.className = cls;
      span.textContent = text;
      card.appendChild(span);
    });
    return card;
  }

  forecastBtn.addEventListener("click", async () => {
    busy(forecastBtn, "Checking…");
    GreenQuote.hide(forecastError);
    const { ok, data } = await GreenQuote.postJson(`/api/quotes/${quoteId}/forecast`);
    if (!ok) {
      forecastError.textContent = data.error || "Couldn't load the forecast.";
      GreenQuote.show(forecastError);
      done(forecastBtn);
      return;
    }
    forecastLocation.textContent = `Next 7 days in ${data.location}.`;
    forecastDays.replaceChildren(...data.days.map((day) => dayCard(day, day.date === data.recommended_date)));
    if (data.recommended_date) {
      forecastDate.textContent = niceDate(data.recommended_date);
      GreenQuote.show(forecastRecommend);
    } else {
      forecastDate.textContent = "none this week";
      GreenQuote.show(forecastRecommend);
    }
    done(forecastBtn, "Refresh forecast");
  });

  proposalBtn.addEventListener("click", async () => {
    busy(proposalBtn, "Drafting…");
    GreenQuote.hide(proposalError);
    const { ok, data } = await GreenQuote.postJson(`/api/quotes/${quoteId}/proposal`);
    if (!ok) {
      proposalError.textContent = data.error || "Couldn't draft the proposal.";
      GreenQuote.show(proposalError);
      done(proposalBtn);
      return;
    }
    proposalText.textContent = data.proposal;
    GreenQuote.show(proposalText);
    GreenQuote.show(copyBtn);
    GreenQuote.hide(proposalEmpty);
    done(proposalBtn, "Redraft");
  });

  copyBtn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(proposalText.textContent);
      copyBtn.textContent = "Copied";
    } catch (error) {
      copyBtn.textContent = "Select the text to copy";
    }
    setTimeout(() => { copyBtn.textContent = "Copy text"; }, 2000);
  });
})();
