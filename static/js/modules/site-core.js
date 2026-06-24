import { $, $$, csrfToken, setToneText } from "./dom.js";


const THEME_KEY = "ai-solution-theme";
const COOKIE_KEY = "ai-solution-cookie-choice";
const RSVP_PENDING_KEY = "ai-solution-rsvp-pending";
const RSVP_PENDING_WINDOW_MS = 120000;
const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
const PHONE_PATTERN = /^[0-9+\-\s()]{7,30}$/;
let iconRefreshScheduled = false;
let adaptiveCardHeightRefresh = () => {};


function smoothBehavior() {
  return reducedMotionQuery.matches ? "auto" : "smooth";
}


function resetLoadingButton(button) {
  if (!button) return;
  if (button.dataset.originalText) {
    button.innerHTML = button.dataset.originalText;
    delete button.dataset.originalText;
  }
  button.classList.remove("is-loading");
  button.disabled = false;
}


function persistThemePreference(theme) {
  window.localStorage.setItem(THEME_KEY, theme);
}


function applyCookiePreferenceState(choice) {
  document.body.dataset.cookiePreference = choice;
  document.documentElement.dataset.cookiePreference = choice;
  if (!window.localStorage.getItem(THEME_KEY)) {
    persistThemePreference(document.documentElement.dataset.theme || "dark");
  }
}


export function refreshIcons() {
  const root = document.documentElement;
  $$("[data-theme-toggle]").forEach((button) => {
    button.innerHTML = root.dataset.theme === "light" ? '<i data-lucide="sun"></i>' : '<i data-lucide="moon"></i>';
    button.setAttribute("aria-pressed", String(root.dataset.theme === "light"));
  });

  if (window.lucide?.createIcons) {
    window.lucide.createIcons();
    return;
  }

  if (!iconRefreshScheduled) {
    iconRefreshScheduled = true;
    window.addEventListener(
      "load",
      () => {
        iconRefreshScheduled = false;
        window.lucide?.createIcons();
      },
      { once: true }
    );
  }
}


function initTheme() {
  const root = document.documentElement;
  const storedTheme = window.localStorage.getItem(THEME_KEY) || "";
  const preferred = window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  root.dataset.theme = storedTheme || preferred;

  $$("[data-theme-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      root.dataset.theme = root.dataset.theme === "light" ? "dark" : "light";
      persistThemePreference(root.dataset.theme);
      refreshIcons();
    });
  });
}


function initNavigation() {
  const navLinks = $("[data-nav-links]");
  const navToggle = $("[data-nav-toggle]");
  const path = window.location.pathname.replace(/\/$/, "") || "/";

  $$(".nav-links a, .admin-sidebar a").forEach((link) => {
    const linkPath = new URL(link.href, window.location.origin).pathname.replace(/\/$/, "") || "/";
    if (linkPath === path) {
      link.classList.add("active");
    }
  });

  if (!navLinks || !navToggle) return;
  navToggle.setAttribute("aria-expanded", "false");
  navToggle.addEventListener("click", () => {
    const isOpen = navLinks.classList.toggle("open");
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });

  document.addEventListener("click", (event) => {
    if (!navLinks.classList.contains("open")) return;
    if (navLinks.contains(event.target) || navToggle.contains(event.target)) return;
    navLinks.classList.remove("open");
    navToggle.setAttribute("aria-expanded", "false");
  });
}


function initReveals() {
  const revealItems = $$(".reveal");
  if (!revealItems.length) return;

  if (reducedMotionQuery.matches || !("IntersectionObserver" in window)) {
    revealItems.forEach((item) => item.classList.add("visible"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("visible");
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.16 }
  );

  revealItems.forEach((item) => observer.observe(item));
}


function initCounters() {
  $$("[data-counter]").forEach((counter) => {
    const rawTarget = counter.dataset.counter || "";
    const suffix = /%$/.test(counter.textContent) ? "%" : "";
    const target = Number.parseInt(rawTarget.replace(/[^0-9]/g, ""), 10);
    if (!Number.isFinite(target)) return;

    if (reducedMotionQuery.matches) {
      counter.textContent = `${target}${suffix}`;
      return;
    }

    let current = 0;
    const step = Math.max(Math.ceil(target / 40), 1);
    const timer = window.setInterval(() => {
      current += step;
      if (current >= target) {
        counter.textContent = `${target}${suffix}`;
        window.clearInterval(timer);
        return;
      }
      counter.textContent = `${current}${suffix}`;
    }, 24);
  });
}


function initFilters() {
  $$("[data-filter-group]").forEach((group) => {
    const buttons = $$("[data-filter]", group);
    const applyFilter = (filter) => {
      buttons.forEach((item) => {
        const active = item.dataset.filter === filter;
        item.classList.toggle("active", active);
        item.setAttribute("aria-pressed", String(active));
      });

      $$("[data-filter-card]").forEach((card) => {
        card.hidden = filter !== "all" && card.dataset.filterCard !== filter;
      });
    };

    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        applyFilter(button.dataset.filter || "all");
        window.requestAnimationFrame(() => adaptiveCardHeightRefresh());
      });
    });

    applyFilter(buttons.find((button) => button.classList.contains("active"))?.dataset.filter || "all");
  });
}


function groupCardsByRow(cards) {
  const rows = [];
  cards.forEach((card) => {
    const top = Math.round(card.getBoundingClientRect().top);
    const existingRow = rows.find((row) => Math.abs(row.top - top) <= 6);
    if (existingRow) {
      existingRow.cards.push(card);
      return;
    }
    rows.push({ top, cards: [card] });
  });
  return rows;
}


function syncRowCardHeights(selector) {
  const cards = $$(selector).filter((card) => !card.hidden);
  cards.forEach((card) => {
    card.style.minHeight = "";
  });
  if (!cards.length || window.innerWidth < 760) return;

  groupCardsByRow(cards).forEach((row) => {
    const maxHeight = Math.max(...row.cards.map((card) => card.getBoundingClientRect().height));
    row.cards.forEach((card) => {
      card.style.minHeight = `${Math.ceil(maxHeight)}px`;
    });
  });
}


function initAdaptiveCardHeights() {
  const refresh = () => {
    syncRowCardHeights(".solution-service-grid .service-card");
    syncRowCardHeights(".industry-index--premium .industry-index-card");
    syncRowCardHeights(".industry-program-grid .industry-program-card");
    syncRowCardHeights(".events-lab-grid .events-lab-card");
    syncRowCardHeights(".events-lab-rail .events-lab-rail-card");
    syncRowCardHeights(".events-lab-metrics article");
  };

  adaptiveCardHeightRefresh = refresh;
  refresh();

  let resizeTimer = 0;
  window.addEventListener("resize", () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(refresh, 120);
  });
  window.addEventListener("load", refresh, { once: true });
}


function initCountdowns() {
  $$("[data-countdown]").forEach((node) => {
    const eventDate = new Date(`${node.dataset.countdown}T00:00:00`);
    function tick() {
      const delta = eventDate.getTime() - Date.now();
      if (delta <= 0) {
        node.textContent = "Event day";
        return;
      }

      const days = Math.floor(delta / 86400000);
      const hours = Math.floor((delta % 86400000) / 3600000);
      node.textContent = `${days}d ${hours}h remaining`;
    }

    tick();
    window.setInterval(tick, 60000);
  });
}


function initQuickScrollButtons() {
  $$("[data-rsvp-event]").forEach((button) => {
    button.addEventListener("click", () => {
      const select = $("#event_id");
      if (select) select.value = button.dataset.rsvpEvent || "";
      $("#rsvp")?.scrollIntoView({ behavior: smoothBehavior(), block: "start" });
    });
  });

  $$("[data-apply-position]").forEach((button) => {
    button.addEventListener("click", () => {
      const select = $("#position");
      if (select) select.value = button.dataset.applyPosition || "";
      $("#apply")?.scrollIntoView({ behavior: smoothBehavior(), block: "start" });
    });
  });
}


function initCarousels() {
  $$("[data-carousel-root]").forEach((carouselRoot) => {
    const track = $("[data-carousel]", carouselRoot);
    if (!track) return;

    const step = () => {
      const firstCard = track.firstElementChild;
      if (!firstCard) return 360;
      const cardStyles = window.getComputedStyle(track);
      const gap = Number.parseFloat(cardStyles.columnGap || cardStyles.gap || "20") || 20;
      return firstCard.getBoundingClientRect().width + gap;
    };

    $("[data-carousel-prev]", carouselRoot)?.addEventListener("click", () => {
      track.scrollBy({ left: -step(), behavior: smoothBehavior() });
    });

    $("[data-carousel-next]", carouselRoot)?.addEventListener("click", () => {
      track.scrollBy({ left: step(), behavior: smoothBehavior() });
    });

    if (carouselRoot.dataset.carouselAuto !== "true" || reducedMotionQuery.matches) {
      return;
    }

    let timerId = null;

    const stop = () => {
      if (!timerId) return;
      window.clearInterval(timerId);
      timerId = null;
    };

    const start = () => {
      stop();
      timerId = window.setInterval(() => {
        const maxScrollLeft = track.scrollWidth - track.clientWidth - 2;
        const next = track.scrollLeft + step();
        track.scrollTo({
          left: next >= maxScrollLeft ? 0 : next,
          behavior: smoothBehavior(),
        });
      }, 5200);
    };

    carouselRoot.addEventListener("mouseenter", stop);
    carouselRoot.addEventListener("mouseleave", start);
    carouselRoot.addEventListener("focusin", stop);
    carouselRoot.addEventListener("focusout", start);
    start();
  });
}


function cookieMode() {
  return document.body.dataset.cookieMode || "remember";
}


function currentCookieChoice() {
  if (cookieMode() === "always") {
    return "";
  }
  return document.body.dataset.cookiePreference || window.localStorage.getItem(COOKIE_KEY) || "";
}


async function saveCookieChoice(choice) {
  const response = await window.fetch("/api/cookie-consent", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken(),
    },
    body: JSON.stringify({ choice }),
  });
  if (!response.ok) {
    throw new Error("cookie save failed");
  }
  if (cookieMode() === "always") {
    window.localStorage.removeItem(COOKIE_KEY);
    return;
  }
  window.localStorage.setItem(COOKIE_KEY, choice);
}


function applyCookieBannerState(showBanner) {
  const banner = $("[data-cookie-banner]");
  if (!banner) return;
  banner.classList.toggle("show", showBanner);
  banner.setAttribute("aria-hidden", String(!showBanner));
  document.body.classList.toggle("cookie-lock", showBanner);
  document.body.classList.toggle("cookie-gated", showBanner);
}


function initCookieConsent() {
  const cookieBanner = $("[data-cookie-banner]");
  const cookiePreferences = $("[data-cookie-preferences]");
  const optionalCookiesToggle = $("[data-cookie-optional]");
  const savePreferencesButton = $("[data-cookie-save-preferences]");
  if (!cookieBanner) return;

  const serverRequiresChoice = document.body.classList.contains("cookie-gated");
  const alwaysShowBanner = cookieMode() === "always";
  const choice = currentCookieChoice();

  if (choice && !alwaysShowBanner) {
    applyCookieBannerState(false);
    if (!document.body.dataset.cookiePreference) {
      applyCookiePreferenceState(choice);
      saveCookieChoice(choice).catch(() => {});
    }
  } else if (serverRequiresChoice || alwaysShowBanner || !choice) {
    applyCookieBannerState(true);
  }

  $$("[data-cookie-manage]").forEach((button) => {
    button.addEventListener("click", () => {
      if (!cookiePreferences) return;
      const isHidden = cookiePreferences.hasAttribute("hidden");
      cookiePreferences.toggleAttribute("hidden");
      cookieBanner.classList.toggle("expanded", isHidden);
      if (!cookiePreferences.hasAttribute("hidden")) {
        optionalCookiesToggle?.focus({ preventScroll: true });
      }
    });
  });

  $("[data-cookie-accept]")?.addEventListener("click", async () => {
    try {
      await saveCookieChoice("accepted");
    } catch (error) {
      if (cookieMode() !== "always") {
        window.localStorage.setItem(COOKIE_KEY, "accepted");
      }
    }
    applyCookiePreferenceState("accepted");
    cookieBanner.classList.remove("expanded");
    applyCookieBannerState(false);
  });

  $("[data-cookie-decline]")?.addEventListener("click", async () => {
    try {
      await saveCookieChoice("declined");
    } catch (error) {
      if (cookieMode() !== "always") {
        window.localStorage.setItem(COOKIE_KEY, "declined");
      }
    }
    applyCookiePreferenceState("declined");
    cookieBanner.classList.remove("expanded");
    applyCookieBannerState(false);
  });

  savePreferencesButton?.addEventListener("click", async () => {
    const optionalCookiesEnabled = optionalCookiesToggle ? optionalCookiesToggle.checked : true;
    const choiceValue = optionalCookiesEnabled ? "customized" : "declined";
    try {
      await saveCookieChoice(choiceValue);
    } catch (error) {
      if (cookieMode() !== "always") {
        window.localStorage.setItem(COOKIE_KEY, choiceValue);
      }
    }
    applyCookiePreferenceState(choiceValue);
    cookieBanner.classList.remove("expanded");
    applyCookieBannerState(false);
  });

  if (optionalCookiesToggle) {
    optionalCookiesToggle.checked = choice !== "declined";
  }
}


function initFeedbackModal() {
  const modal = $("[data-feedback-modal]");
  const form = $("[data-feedback-form]", modal || document);
  if (!modal || !form) return;

  const status = $("[data-feedback-status]", modal);
  const submitButton = $("button[type='submit']", form);
  const openButtons = $$("[data-feedback-open]");
  const closeButtons = $$("[data-feedback-close]", modal);
  const trackedFields = $$("[data-feedback-field]", modal);
  let lastTrigger = null;

  const resetModalState = () => {
    modal.hidden = true;
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("feedback-modal-open");
    form.dataset.feedbackSubmitting = "false";
    if (submitButton) {
      submitButton.disabled = false;
      if (submitButton.dataset.originalText) {
        submitButton.innerHTML = submitButton.dataset.originalText;
        delete submitButton.dataset.originalText;
      }
    }
  };

  const setStatus = (message, tone = "neutral") => {
    if (!status) return;
    if (!message) {
      status.hidden = true;
      status.textContent = "";
      delete status.dataset.tone;
      return;
    }
    status.hidden = false;
    setToneText(status, message, tone);
  };

  const clearErrors = () => {
    $$("[data-feedback-error]", modal).forEach((node) => {
      node.textContent = "";
    });
    trackedFields.forEach((field) => {
      field.classList.remove("is-invalid");
    });
    $$("input, textarea, select", form).forEach((control) => {
      control.removeAttribute("aria-invalid");
    });
  };

  const openModal = (trigger) => {
    lastTrigger = trigger || document.activeElement;
    modal.hidden = false;
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("feedback-modal-open");
    clearErrors();
    setStatus("");
    window.requestAnimationFrame(() => {
      $("[name='full_name']", form)?.focus({ preventScroll: true });
    });
  };

  const closeModal = () => {
    resetModalState();
    clearErrors();
    setStatus("");
    if (lastTrigger && typeof lastTrigger.focus === "function") {
      lastTrigger.focus({ preventScroll: true });
    }
  };

  const renderErrors = (errors = {}) => {
    clearErrors();
    Object.entries(errors).forEach(([fieldName, messages]) => {
      const message = Array.isArray(messages) ? messages.join(" ") : String(messages || "");
      const errorNode = $(`[data-feedback-error="${fieldName}"]`, modal);
      const fieldWrapper = $(`[data-feedback-field="${fieldName}"]`, modal);
      const controls = $$(`[name="${fieldName}"]`, form);
      if (errorNode) {
        errorNode.textContent = message;
      }
      if (fieldWrapper) {
        fieldWrapper.classList.add("is-invalid");
      }
      controls.forEach((control) => {
        control.setAttribute("aria-invalid", "true");
      });
    });
  };

  openButtons.forEach((button) => {
    button.addEventListener("click", () => openModal(button));
  });

  closeButtons.forEach((button) => {
    button.addEventListener("click", closeModal);
  });

  modal.addEventListener("click", (event) => {
    if (event.target === modal || event.target.closest("[data-feedback-close]")) {
      closeModal();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && modal.classList.contains("is-open")) {
      closeModal();
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (form.dataset.feedbackSubmitting === "true") return;

    form.dataset.feedbackSubmitting = "true";
    clearErrors();
    setStatus("Sending feedback securely...", "progress");

    if (submitButton) {
      submitButton.dataset.originalText = submitButton.innerHTML;
      submitButton.innerHTML = "Sending...";
      submitButton.disabled = true;
    }

    try {
      const response = await window.fetch(form.action, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": csrfToken(),
        },
        body: new window.FormData(form),
      });
      const payload = await response.json().catch(() => ({}));

      if (!response.ok || !payload.ok) {
        renderErrors(payload.errors || {});
        setStatus(payload.message || "Please correct the highlighted feedback fields and try again.", payload.tone || "warning");
        return;
      }

      form.reset();
      setStatus(payload.message || "Thanks for your feedback. We will review it shortly.", payload.tone || "success");
      window.setTimeout(() => {
        closeModal();
      }, 1400);
    } catch (error) {
      setStatus("Feedback could not be sent right now. Please try again.", "warning");
    } finally {
      form.dataset.feedbackSubmitting = "false";
      if (submitButton) {
        submitButton.disabled = false;
        if (submitButton.dataset.originalText) {
          submitButton.innerHTML = submitButton.dataset.originalText;
          delete submitButton.dataset.originalText;
        }
      }
    }
  });

  resetModalState();
  window.addEventListener("pageshow", resetModalState);
}


function initEventRsvpForm() {
  const form = $("[data-event-rsvp-form]");
  if (!form) {
    window.sessionStorage.removeItem(RSVP_PENDING_KEY);
    return;
  }

  const rsvpSection = $("#rsvp");
  const feedback = $("[data-rsvp-feedback]", form);
  const phoneInput = $("#phone", form);
  const emailInput = $("#email", form);
  const nameInput = $("#full_name", form);
  const eventInput = $("#event_id", form);
  const submitButton = $("button[type='submit']", form);
  const selectedEvent = new URLSearchParams(window.location.search).get("event");

  const readPendingSubmission = () => {
    const raw = window.sessionStorage.getItem(RSVP_PENDING_KEY);
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      if (Date.now() - Number(parsed.timestamp || 0) > RSVP_PENDING_WINDOW_MS) {
        window.sessionStorage.removeItem(RSVP_PENDING_KEY);
        return null;
      }
      return parsed;
    } catch (error) {
      window.sessionStorage.removeItem(RSVP_PENDING_KEY);
      return null;
    }
  };

  const updateFeedback = (message, tone = "neutral") => {
    if (!feedback) return;
    if (!message) {
      feedback.hidden = true;
      feedback.textContent = "";
      delete feedback.dataset.tone;
      return;
    }
    feedback.hidden = false;
    setToneText(feedback, message, tone);
  };

  const validatePhone = () => {
    if (!phoneInput) return true;
    phoneInput.value = phoneInput.value.replace(/\s+/g, " ").trim();
    const valid = PHONE_PATTERN.test(phoneInput.value);
    phoneInput.setCustomValidity(valid ? "" : "Enter a valid phone number using 7 to 30 digits and symbols.");
    return valid;
  };

  const validateEmail = () => {
    if (!emailInput) return true;
    emailInput.value = emailInput.value.trim();
    emailInput.setCustomValidity(emailInput.validity.typeMismatch ? "Enter a valid email address." : "");
    return emailInput.checkValidity();
  };

  const clearPendingSubmission = () => {
    window.sessionStorage.removeItem(RSVP_PENDING_KEY);
    form.removeAttribute("aria-busy");
  };

  if (($(".flash.success") || $(".flash.error")) && readPendingSubmission()) {
    clearPendingSubmission();
  }

  updateFeedback("");

  if (selectedEvent) {
    updateFeedback("Your selected event is ready below. Complete the registration form to confirm attendance.");
    window.setTimeout(() => {
      rsvpSection?.scrollIntoView({ behavior: smoothBehavior(), block: "start" });
      eventInput?.focus({ preventScroll: true });
    }, 180);
  }

  phoneInput?.addEventListener("input", validatePhone);
  phoneInput?.addEventListener("blur", validatePhone);
  emailInput?.addEventListener("input", validateEmail);
  emailInput?.addEventListener("blur", validateEmail);

  form.addEventListener(
    "invalid",
    () => {
      updateFeedback("Review the highlighted RSVP details before submitting again.", "warning");
      resetLoadingButton(submitButton);
      form.removeAttribute("aria-busy");
    },
    true
  );

  form.addEventListener("submit", (event) => {
    validateEmail();
    validatePhone();
    const fingerprint = [
      eventInput?.value || "",
      (emailInput?.value || "").trim().toLowerCase(),
      (nameInput?.value || "").trim().toLowerCase(),
    ].join("|");
    const pending = readPendingSubmission();

    if (pending?.fingerprint && pending.fingerprint === fingerprint) {
      event.preventDefault();
      event.stopImmediatePropagation();
      updateFeedback("This RSVP is already being processed. Please wait for confirmation before submitting again.", "warning");
      resetLoadingButton(submitButton);
      form.removeAttribute("aria-busy");
      return;
    }

    window.sessionStorage.setItem(
      RSVP_PENDING_KEY,
      JSON.stringify({
        fingerprint,
        timestamp: Date.now(),
      })
    );
    if (nameInput) {
      nameInput.value = nameInput.value.trim();
    }
    form.setAttribute("aria-busy", "true");
    updateFeedback("Submitting RSVP securely. Please wait while we validate your details...", "progress");
  });
}


function recaptchaActionFromForm(form) {
  const scope = $("input[name='captcha_scope']", form)?.value || form.dataset.recaptchaAction || "submit";
  return scope.replace(/[^\w/]/g, "_") || "submit";
}


function initRecaptcha() {
  const siteKey = document.body.dataset.recaptchaSiteKey || "";
  if (!siteKey) return;

  $$("form").forEach((form) => {
    const tokenInput = $("input[name='recaptcha_token']", form);
    if (!tokenInput) return;

    form.addEventListener(
      "submit",
      (event) => {
        if (tokenInput.value || form.dataset.recaptchaPending === "true") return;
        if (!window.grecaptcha?.execute || !window.grecaptcha?.ready) return;

        event.preventDefault();
        form.dataset.recaptchaPending = "true";
        window.grecaptcha.ready(() => {
          window.grecaptcha
            .execute(siteKey, { action: recaptchaActionFromForm(form) })
            .then((token) => {
              tokenInput.value = token || "";
              form.dataset.recaptchaPending = "false";
              form.requestSubmit();
            })
            .catch(() => {
              form.dataset.recaptchaPending = "false";
              form.requestSubmit();
            });
        });
      },
      true
    );
  });
}


function initForms() {
  $$("[data-password-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const wrapper = button.closest(".password-control");
      const input = $("input", wrapper);
      if (!input) return;

      const visible = input.type === "text";
      input.type = visible ? "password" : "text";
      button.textContent = visible ? "Show" : "Hide";
      button.setAttribute("aria-label", visible ? "Show password" : "Hide password");
    });
  });

  $$("[data-loading-text]").forEach((button) => {
    button.closest("form")?.addEventListener("submit", () => {
      if (button.disabled) return;
      button.dataset.originalText = button.innerHTML;
      button.innerHTML = button.dataset.loadingText || "Working...";
      button.classList.add("is-loading");
      button.disabled = true;
    });
  });

  const tabRoot = $("[data-auth-tabs]");
  const panelsRoot = $("[data-auth-panels]");
  if (tabRoot && panelsRoot) {
    const activatePanel = (name) => {
      $$("[data-auth-target]", tabRoot).forEach((button) => {
        button.classList.toggle("active", button.dataset.authTarget === name);
      });
      $$("[data-auth-panel]", panelsRoot).forEach((panel) => {
        panel.classList.toggle("active", panel.dataset.authPanel === name);
      });

      const url = new URL(window.location.href);
      url.searchParams.set("panel", name);
      window.history.replaceState({}, "", url);
      $(`[data-auth-panel="${name}"] input:not([type="hidden"])`, panelsRoot)?.focus({ preventScroll: true });
    };

    activatePanel(panelsRoot.dataset.activePanel || "login");
    $$("[data-auth-target]", tabRoot).forEach((button) => {
      button.addEventListener("click", () => activatePanel(button.dataset.authTarget || "login"));
    });
    $$("[data-auth-trigger]").forEach((button) => {
      button.addEventListener("click", () => activatePanel(button.dataset.authTrigger || "login"));
    });
  }
}


function initFaqItems() {
  $$(".faq-item").forEach((item) => {
    item.addEventListener("toggle", () => {
      const icon = $("i", item);
      if (!icon) return;
      icon.setAttribute("data-lucide", item.open ? "minus" : "plus");
      refreshIcons();
    });
  });
}


function initAdminMenu() {
  $("[data-admin-menu]")?.addEventListener("click", () => {
    $(".admin-sidebar")?.classList.toggle("open");
  });
}


export function initSite() {
  initTheme();
  initNavigation();
  initReveals();
  initCounters();
  initFilters();
  initAdaptiveCardHeights();
  initCountdowns();
  initQuickScrollButtons();
  initCarousels();
  initCookieConsent();
  initFeedbackModal();
  initEventRsvpForm();
  initRecaptcha();
  initForms();
  initFaqItems();
  initAdminMenu();
  refreshIcons();
  window.addEventListener("load", refreshIcons, { once: true });
}
