(() => {
  const form = document.getElementById("quote-form");
  if (!form) return;

  const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$/;
  const NAME_PATTERN = /^[A-Za-z][A-Za-z .,'&-]{1,79}$/;
  const CITY_PATTERN = /^[A-Za-z][A-Za-z .'-]{1,59}$/;

  const serviceInputs = Array.from(form.querySelectorAll("[data-service]"));
  const notes = document.getElementById("notes");
  const notesCount = document.getElementById("notes-count");
  const status = document.getElementById("sum-status");
  let timer = null;
  let requestNumber = 0;

  function setError(name, message) {
    const slot = form.querySelector(`.field-error[data-for="${name}"]`);
    if (slot) slot.textContent = message || "";
    const input = form.elements[name];
    const field = input && input.closest ? input.closest(".field") : null;
    if (field) field.classList.toggle("has-error", Boolean(message));
  }

  function numberIn(input, min, max) {
    if (input.value.trim() === "") return true;
    const value = Number(input.value);
    return Number.isFinite(value) && value >= min && value <= max;
  }

  function validate() {
    const errors = {};
    const value = (name) => form.elements[name].value.trim();

    if (!NAME_PATTERN.test(value("customer_name"))) {
      errors.customer_name = "Enter the customer's name (letters only, 2-80 characters).";
    }
    if (!EMAIL_PATTERN.test(value("customer_email"))) {
      errors.customer_email = "Enter a valid email address.";
    }
    const phoneDigits = value("customer_phone").replace(/\D/g, "");
    if (phoneDigits && phoneDigits.length !== 10) {
      errors.customer_phone = "Phone number should be 10 digits, or leave it blank.";
    }
    if (!CITY_PATTERN.test(value("city"))) {
      errors.city = "Enter the job site's city.";
    }
    if (!numberIn(form.elements.travel_miles, 0, 60)) {
      errors.travel_miles = "Travel distance must be between 0 and 60 miles.";
    }

    let anyService = false;
    serviceInputs.forEach((input) => {
      const max = Number(input.dataset.max);
      if (!numberIn(input, 0, max)) {
        errors[input.name] = `${input.dataset.label} must be between 0 and ${max}.`;
      } else if (Number(input.value) > 0) {
        anyService = true;
      }
    });
    if (!anyService) {
      errors.services = "Add a quantity for at least one service.";
    }

    const names = ["customer_name", "customer_email", "customer_phone", "city", "travel_miles", "services"]
      .concat(serviceInputs.map((input) => input.name));
    names.forEach((name) => setError(name, errors[name]));
    return errors;
  }

  function collect() {
    const data = {};
    new FormData(form).forEach((value, key) => {
      if (key !== "csrf_token") data[key] = value;
    });
    return data;
  }

  function render(result) {
    document.getElementById("sum-total").textContent = GreenQuote.money(result.total);
    document.getElementById("sum-labor").textContent = GreenQuote.money(result.labor_total);
    document.getElementById("sum-materials").textContent = GreenQuote.money(result.material_total);
    document.getElementById("sum-discount").textContent = result.discount ? "-" + GreenQuote.money(result.discount) : GreenQuote.money(0);
    document.getElementById("sum-travel").textContent = GreenQuote.money(result.travel_fee);
    document.getElementById("sum-minimum").textContent = GreenQuote.money(result.minimum_adjustment);
    document.getElementById("sum-tax").textContent = GreenQuote.money(result.tax);
    document.getElementById("sum-deposit").textContent = GreenQuote.money(result.deposit);
    document.getElementById("sum-crew").textContent = result.labor_hours
      ? `${result.labor_hours} labor hrs · about ${result.crew_days} crew day${result.crew_days === 1 ? "" : "s"}`
      : "Enter at least one service.";
  }

  async function refreshEstimate() {
    const hasService = serviceInputs.some((input) => Number(input.value) > 0);
    if (!hasService) {
      render({ minimum_adjustment: 0, total: 0, labor_total: 0, material_total: 0, discount: 0, travel_fee: 0, tax: 0, deposit: 0, labor_hours: 0 });
      status.textContent = "";
      return;
    }
    const thisRequest = ++requestNumber;
    status.textContent = "Calculating…";
    const { ok, data } = await GreenQuote.postJson("/api/estimate", collect());
    if (thisRequest !== requestNumber) return;
    if (ok) {
      render(data);
      status.textContent = "";
    } else {
      status.textContent = data.errors ? Object.values(data.errors)[0] : data.error;
    }
  }

  function scheduleEstimate() {
    clearTimeout(timer);
    timer = setTimeout(refreshEstimate, 300);
  }

  function updateNotesCount() {
    notesCount.textContent = notes.value.length;
  }

  form.addEventListener("input", (event) => {
    if (event.target === notes) {
      updateNotesCount();
      return;
    }
    scheduleEstimate();
  });
  form.addEventListener("change", scheduleEstimate);

  form.addEventListener("submit", (event) => {
    const errors = validate();
    if (Object.keys(errors).length > 0) {
      event.preventDefault();
      const firstBad = form.querySelector(".has-error input, .has-error select, .has-error textarea");
      if (firstBad) firstBad.focus();
      status.textContent = "Fix the highlighted fields before saving.";
      return;
    }
    document.getElementById("save-btn").disabled = true;
    document.getElementById("save-btn").textContent = "Saving…";
  });

  updateNotesCount();
  refreshEstimate();
})();
