/* CVStand builder — form generation, live preview, autosave, template drawer.
   Vanilla JS, no build step. */
(() => {
  "use strict";

  const S = window.__STATE__;
  const EP = S.endpoints;
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /* ---------- where the résumé lives ----------
     The BROWSER owns it. The server used to, in one global data/resume.json,
     which is right for a tool on your own machine and is the one thing that
     cannot survive a public URL: two visitors read and overwrite each other's
     document, with no bug anywhere in the code.

     localStorage instead — per browser by construction, no account needed to
     be safe, and the CV never reaches the server's disk. The server is handed
     the document only to render or export it, and keeps nothing.

     The page still ships #resume-data. It is the SEED, not the store: what a
     first-time visitor starts from. A stored résumé always wins over it.

     Reads and writes are wrapped because localStorage throws outright in some
     configurations (private windows, site data blocked) rather than returning
     null — an uncaught throw here would take the whole builder down at boot,
     for a feature the user could live without. */
  const STORE_KEY = "cvstand:resume";
  const TPL_KEY = "cvstand:template";

  function readStored(key) {
    try { return window.localStorage.getItem(key); } catch (_) { return null; }
  }
  function writeStored(key, value) {
    try { window.localStorage.setItem(key, value); return true; } catch (_) { return false; }
  }

  const seed = JSON.parse($("#resume-data").textContent);
  let data = (() => {
    const raw = readStored(STORE_KEY);
    if (!raw) return seed;
    try {
      const parsed = JSON.parse(raw);
      /* A stored value that is not an object is corrupt, not empty. Falling
         back to the seed beats booting the form against a string. */
      return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : seed;
    } catch (_) { return seed; }
  })();
  const catalogue = JSON.parse($("#catalogue-data").textContent);
  let templateKey = readStored(TPL_KEY) || S.templateKey;
  /* A key stored by an older build could name a template that no longer
     exists or was never ported; the drawer would then show nothing selected
     and the preview would 400. */
  if (!catalogue.some((t) => t.key === templateKey && t.ported)) templateKey = S.templateKey;

  /* Interface strings and level vocabularies, handed over by the server.
     Two different languages on purpose: T() follows the READER (the ui_lang
     cookie) while the level lists follow the RESUME, because a level word is
     stored in the document and printed on the page. See app/i18n.py.

     SKILL and LANGUAGE levels are separate lists. They used to be one list of
     eight, so a skill could be set to "Fluent" - a word LEVEL_DOTS does not
     map and which is not "unrated" either, so the macros drew five dots with
     zero filled beside it. */
  const I18N = JSON.parse($("#i18n-data").textContent);
  /* Folds the msgid the same way the server does (whitespace collapsed,
     lower-cased), because the two catalogues behind it are cased
     differently. English ships an empty table: the msgid IS the English
     string, so T() returning its argument is the whole English path. */
  const fold = (s) => String(s).trim().replace(/\s+/g, " ").toLowerCase();
  const T = (s) => (I18N.strings && I18N.strings[fold(s)]) || s;
  /* COPIES, not the payload's own arrays. The language control swaps these
     IN PLACE (see applyLevelVocab) so that SPEC's `options:` references stay
     live across a re-render; mutating the payload would corrupt the other
     language's list we are about to switch to. */
  const SKILL_LEVELS = I18N.levels.skill.slice();
  const LANGUAGE_LEVELS = I18N.levels.language.slice();
  /* The DOCUMENT's language. Not the reader's - T() above follows the cookie,
     this follows the file (app/i18n.py). Held here as well as in `data.lang`
     because the remap needs to know which language the stored level words are
     IN, and by the time the change event fires `data.lang` is already the new
     one. */
  const DOC_LANGS = I18N.doc_langs || ["en"];
  let docLang = I18N.doc_lang || "en";

  /* Autonyms: a language names itself the same way whoever is reading, which
     is why these are not in the translation catalogue. Same convention as the
     header's interface switcher (EN / العربية). */
  const DOC_LANG_NAMES = { en: "English", ar: "العربية" };

  function applyLevelVocab(lang) {
    const lv = (I18N.levels_by_lang && I18N.levels_by_lang[lang]) || I18N.levels;
    SKILL_LEVELS.length = 0; SKILL_LEVELS.push.apply(SKILL_LEVELS, lv.skill);
    LANGUAGE_LEVELS.length = 0; LANGUAGE_LEVELS.push.apply(LANGUAGE_LEVELS, lv.language);
  }

  const F = (path, label, opts = {}) => Object.assign({ path, label }, opts);

  const SPEC = [
    { id: "basics", title: T("Basics"), fields: [
      F("name", T("Full name"), { ph: T("Wren Ashworth") }),
      F("title", T("Headline / role"), { ph: T("Creative Lead") }),
      F("summary", T("Professional summary"), { type: "textarea" }),
      F("summary_highlight", T("Phrase to highlight"), { hint: T("Must appear word-for-word in the summary above") }),
      F("photo_url", T("Photo"), { type: "photo" }),
      F("lang", T("Résumé language"), { type: "doclang",
        hint: T("The language the résumé is written in — sets its direction, its headings and its level words. Not the interface language.") }),
    ]},
    { id: "contact", title: T("Contact"), fields: [
      F("contact.email", T("Email")),
      F("contact.phone", T("Phone")),
      F("contact.address", T("Location")),
      F("contact.site", T("Website")),
    ], list: { path: "contact.social", label: T("Social link"), item: [F("label", T("Label")), F("url", T("URL"))] } },
    { id: "achievements", title: T("Stat chips"), hint: T("Up to 4 appear on the résumé. A blank metric hides the whole chip."),
      list: { path: "achievements", label: T("Stat"), item: [F("metric", T("Metric"), { ph: "$3.2M"  /* a currency example, not a label */ }), F("label", T("Caption"), { ph: T("Budget owned") })] } },
    { id: "experience", title: T("Experience"),
      list: { path: "experience", label: T("Role"), titleKey: "role", bullets: true,
        item: [F("role", T("Job title")), F("company", T("Company")), F("location", T("Location")), F("start", T("Start")), F("end", T("End"))] } },
    { id: "education", title: T("Education"),
      list: { path: "education", label: T("Qualification"), titleKey: "degree", bullets: true,
        item: [F("degree", T("Degree")), F("school", T("School")), F("start", T("Start")), F("end", T("End")), F("gpa", T("GPA"))] } },
    { id: "recognition", title: T("Recognition"),
      list: { path: "recognition", label: T("Award"), titleKey: "title", item: [F("title", T("Title")), F("detail", T("Detail"))] } },
    { id: "skills", title: T("Skills"), hint: T("The level word shows as text and as a 5-dot level."),
      list: { path: "skills", label: T("Skill"), titleKey: "name",
        item: [F("name", T("Skill")), F("level", T("Level"), { type: "select", options: SKILL_LEVELS }), F("percent", T("Percent (bars/rings only)"), { type: "number" })] } },
    { id: "tools", title: T("Tools"), list: { path: "tools", label: T("Tool"), string: true } },
    { id: "languages", title: T("Languages"),
      list: { path: "languages", label: T("Language"), titleKey: "name", item: [F("name", T("Language")), F("level", T("Level"), { type: "select", options: LANGUAGE_LEVELS })] } },
    { id: "references", title: T("References"),
      list: { path: "references", label: T("Reference"), titleKey: "name",
        item: [F("name", T("Name")), F("title", T("Title")), F("phone", T("Phone")), F("email", T("Email"))] } },
  ];

  /* ---------- path helpers ---------- */
  function getPath(obj, path) {
    return path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), obj);
  }
  function setPath(obj, path, val) {
    const keys = path.split(".");
    let o = obj;
    for (let i = 0; i < keys.length - 1; i++) {
      const k = keys[i], nextIsIdx = /^\d+$/.test(keys[i + 1]);
      if (o[k] == null) o[k] = nextIsIdx ? [] : {};
      o = o[k];
    }
    o[keys[keys.length - 1]] = val;
  }
  function ensureArray(path) {
    if (!Array.isArray(getPath(data, path))) setPath(data, path, []);
    return getPath(data, path);
  }

  /* ---------- form rendering ---------- */
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function inputHTML(fld, path) {
    const val = getPath(data, path);
    const id = "f_" + path.replace(/\W/g, "_");
    if (fld.type === "photo") {
      return `<div class="field">
        <label for="${id}">${fld.label}</label>
        <div style="display:flex;gap:10px;align-items:center">
          <input type="file" id="${id}" accept="image/png,image/jpeg,image/webp" data-photo="${path}">
          ${val ? `<img src="${esc(val)}" alt="" style="width:44px;height:44px;border-radius:50%;object-fit:cover;border:1px solid var(--line)">` : ""}
          ${val ? `<button type="button" class="rm" data-clear-photo="${path}">${T("Remove")}</button>` : ""}
        </div>
      </div>`;
    }
    if (fld.type === "doclang") {
      /* An absent `lang` means English (schema.lang_of) - the degrade path that
         kept every pre-bilingual résumé working - so the control shows English
         rather than a blank, and writes nothing until the user picks. */
      const cur = DOC_LANGS.indexOf(val) >= 0 ? val : "en";
      const opts = DOC_LANGS.map((code) =>
        `<option value="${esc(code)}" lang="${esc(code)}"${code === cur ? " selected" : ""}>${esc(DOC_LANG_NAMES[code] || code)}</option>`);
      return `<div class="field"><label for="${id}">${fld.label}</label>
        <select id="${id}" name="${path}" data-doc-lang>${opts.join("")}</select>
        ${fld.hint ? `<small style="color:var(--muted);font-size:11.5px">${fld.hint}</small>` : ""}</div>`;
    }
    if (fld.type === "textarea") {
      return `<div class="field"><label for="${id}">${fld.label}</label>
        <textarea id="${id}" name="${path}">${esc(val)}</textarea>
        ${fld.hint ? `<small style="color:var(--muted);font-size:11.5px">${fld.hint}</small>` : ""}</div>`;
    }
    if (fld.type === "select") {
      const opts = ['<option value=""></option>'].concat(
        (fld.options || []).map((o) => `<option${o === val ? " selected" : ""}>${esc(o)}</option>`)
      );
      const custom = val && !(fld.options || []).includes(val) ? `<option selected>${esc(val)}</option>` : "";
      return `<div class="field"><label for="${id}">${fld.label}</label>
        <select id="${id}" name="${path}">${opts.join("")}${custom}</select></div>`;
    }
    const t = fld.type === "number" ? "number" : "text";
    return `<div class="field"><label for="${id}">${fld.label}</label>
      <input type="${t}" id="${id}" name="${path}" value="${esc(val)}" ${fld.ph ? `placeholder="${esc(fld.ph)}"` : ""}>
      ${fld.hint ? `<small style="color:var(--muted);font-size:11.5px">${fld.hint}</small>` : ""}</div>`;
  }

  function entryHTML(listCfg, idx) {
    const base = `${listCfg.path}.${idx}`;
    if (listCfg.string) {
      return `<div class="bullet-row">
        <input type="text" name="${base}" value="${esc(getPath(data, base))}" placeholder="${esc(listCfg.label)}">
        <button type="button" data-act="rm" data-path="${listCfg.path}" data-idx="${idx}">×</button>
      </div>`;
    }
    const entry = getPath(data, base) || {};
    const title = listCfg.titleKey ? (entry[listCfg.titleKey] || `${listCfg.label} ${idx + 1}`) : `${listCfg.label} ${idx + 1}`;
    const pairs = listCfg.item;
    let inner = "";
    for (let i = 0; i < pairs.length; i += 2) {
      const a = pairs[i], b = pairs[i + 1];
      inner += b
        ? `<div class="grid-2">${inputHTML(a, base + "." + a.path)}${inputHTML(b, base + "." + b.path)}</div>`
        : inputHTML(a, base + "." + a.path);
    }
    let bullets = "";
    if (listCfg.bullets) {
      const arr = Array.isArray(entry.bullets) ? entry.bullets : [];
      bullets = `<div class="bullets"><label style="font-size:12px;font-weight:600;color:var(--muted)">${T("Bullet points")}</label>
        ${arr.map((b, bi) => `<div class="bullet-row">
          <input type="text" name="${base}.bullets.${bi}" value="${esc(b)}">
          <button type="button" data-act="rmbullet" data-path="${base}.bullets" data-idx="${bi}">×</button>
        </div>`).join("")}
        <button type="button" class="add" data-act="addbullet" data-path="${base}.bullets" style="margin-top:8px">${T("+ Add bullet")}</button></div>`;
    }
    return `<div class="entry">
      <div class="entry-head"><b>${esc(title)}</b>
        <button type="button" class="rm" data-act="rm" data-path="${listCfg.path}" data-idx="${idx}">${T("Remove")}</button></div>
      ${inner}${bullets}
    </div>`;
  }

  function sectionHTML(sec, n) {
    let body = "";
    (sec.fields || []).forEach((f) => { body += inputHTML(f, f.path); });
    if (sec.hint) body += `<p style="font-size:12px;color:var(--muted);margin:12px 0 0">${sec.hint}</p>`;
    if (sec.list) {
      const arr = Array.isArray(getPath(data, sec.list.path)) ? getPath(data, sec.list.path) : [];
      body += `<div data-list="${sec.list.path}">`;
      arr.forEach((_, i) => { body += entryHTML(sec.list, i); });
      /* Composed, not one msgid per list: `sec.list.label` is ALREADY through
         T() where the section was declared, so translating only the verb keeps
         the two halves in one language. English is byte-identical — T("+ Add")
         returns "+ Add" — so the golden HTML gate does not move. */
      body += `</div><button type="button" class="add" data-act="add" data-path="${sec.list.path}">${T("+ Add")} ${sec.list.label.toLowerCase()}</button>`;
    }
    const open = n <= 2 ? " open" : "";
    return `<details class="sec"${open}><summary><span class="num">${n}</span>${sec.title}<span class="caret">›</span></summary>
      <div class="sec-body">${body}</div></details>`;
  }

  function renderForm() {
    const openIds = new Set($$("#resume-form .sec[open]").map((d) => d.dataset.sid));
    const form = $("#resume-form");
    $$(".sec", form).forEach((n) => n.remove());
    let html = "";
    SPEC.forEach((sec, i) => { html += sectionHTML(sec, i + 1); });
    form.insertAdjacentHTML("beforeend", html);
    $$("#resume-form .sec").forEach((d, i) => {
      d.dataset.sid = SPEC[i].id;
      if (openIds.size) d.open = openIds.has(SPEC[i].id);
    });
  }

  /* ---------- change handling ---------- */
  let renderTimer, saveTimer, savePending = false;
  function onChange(structural) {
    if (structural) renderForm();
    scheduleRender();
    scheduleSave();
  }
  function scheduleRender() {
    clearTimeout(renderTimer);
    renderTimer = setTimeout(doRender, 350);
  }
  function scheduleSave() {
    savePending = true;
    setSaveState("unsaved");
    clearTimeout(saveTimer);
    saveTimer = setTimeout(doSave, 900);
  }

  function coerce(name, raw) {
    if (name.endsWith(".percent")) return raw === "" ? undefined : Math.max(0, Math.min(100, parseInt(raw, 10) || 0));
    return raw;
  }

  $("#resume-form").addEventListener("input", (e) => {
    const el = e.target;
    if (el.dataset.photo !== undefined) return;
    if (!el.name) return;
    const v = coerce(el.name, el.value);
    if (v === undefined) {
      const keys = el.name.split(".");
      const parent = getPath(data, keys.slice(0, -1).join("."));
      if (parent) delete parent[keys[keys.length - 1]];
    } else {
      setPath(data, el.name, v);
    }
    // keep entry-head titles fresh without stealing focus
    const head = el.closest(".entry")?.querySelector(".entry-head b");
    const sec = SPEC.find((s) => s.list && el.name.startsWith(s.list.path + "."));
    if (head && sec && sec.list.titleKey && el.name.endsWith("." + sec.list.titleKey)) head.textContent = el.value || head.textContent;
    scheduleRender();
    scheduleSave();
  });

  $("#resume-form").addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-act]");
    if (!btn) return;
    const { act, path, idx } = btn.dataset;
    if (act === "add") {
      const sec = SPEC.find((s) => s.list && s.list.path === path);
      const arr = ensureArray(path);
      arr.push(sec.list.string ? "" : (sec.list.bullets ? { bullets: [] } : {}));
    } else if (act === "rm") {
      ensureArray(path).splice(+idx, 1);
    } else if (act === "addbullet") {
      ensureArray(path).push("");
    } else if (act === "rmbullet") {
      ensureArray(path).splice(+idx, 1);
    } else return;
    onChange(true);
  });

  /* photo upload */
  $("#resume-form").addEventListener("change", async (e) => {
    const el = e.target;
    if (el.dataset.clearPhoto !== undefined) return;
    if (el.dataset.photo === undefined || !el.files || !el.files[0]) return;
    const fd = new FormData();
    fd.append("photo", el.files[0]);
    setSaveState("saving");
    /* A REJECTED UPLOAD HAS TO SAY SO. `/api/photo` answers a bad file with
       `abort(415)`, which is an HTML error page — so `res.json()` throws on the
       failure path. Catching and ignoring that (as this did) left the indicator
       reading T("Saving…") for ever and told the user nothing at all about why no
       photo appeared. Check the status before parsing, surface the reason, and
       always hand the save indicator back to whatever is actually true. */
    try {
      const res = await fetch(EP.photo, { method: "POST", body: fd });
      if (!res.ok) {
        /* The server names the reason (JSON `error`) because only it has read
           the bytes: "not a photo" and "damaged photo" both arrive as 415 and
           are not the same advice. The status-code fallback is for a failure
           upstream of the handler, where there is no reason to be had. */
        let reason = T("The photo could not be uploaded (error ") + res.status + ").";
        try {
          const j = await res.json();
          if (j && j.error) reason = j.error;
        } catch (_) { /* not JSON — keep the status-code wording */ }
        showErrors([reason]);
        el.value = "";                    // so the same file can be retried
        restoreSaveState();
        return;
      }
      const j = await res.json();
      showErrors(null);
      setPath(data, el.dataset.photo, j.url);
      onChange(true);
    } catch (_) {
      showErrors([T("The photo could not be uploaded — the server did not answer.")]);
      el.value = "";
      restoreSaveState();
    }
  });
  $("#resume-form").addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-clear-photo]");
    if (!btn) return;
    setPath(data, btn.dataset.clearPhoto, "");
    onChange(true);
  });

  /* ---------- the document's language ---------- */
  /* Changing this changes the DOCUMENT, not the interface: `dir`, the section
     headings, the Arabic font sheet and which Word master the export takes all
     hang off `resume.lang`. The header switcher is the other language and is
     deliberately unrelated (app/i18n.py) - nothing in here reads the cookie.

     Until this control existed, `lang` was reachable only by hand-editing
     data/resume.json, so a bilingual user could type Arabic and had no way to
     say the résumé was Arabic: it rendered ltr with English headings. */

  /* The words already stored, paired with what they would become. The two
     vocabularies are index-aligned and strongest-first in both languages
     (labels.all_levels, gated by tests/test_document_language.py), so position
     is the translation. Anything the user typed themselves is not in either
     list and is left alone. */
  function levelRemapPlan(from, to) {
    const by = I18N.levels_by_lang || {};
    if (!by[from] || !by[to]) return [];
    const plan = [];
    [["skills", "skill"], ["languages", "language"]].forEach((pair) => {
      const arr = getPath(data, pair[0]);
      if (!Array.isArray(arr)) return;
      const src = by[from][pair[1]], dst = by[to][pair[1]];
      arr.forEach((entry, i) => {
        if (!entry || typeof entry !== "object") return;
        const at = src.indexOf(entry.level);
        if (at >= 0 && dst[at] && dst[at] !== entry.level) {
          plan.push({ path: pair[0] + "." + i + ".level", to: dst[at], from: entry.level });
        }
      });
    });
    return plan;
  }

  $("#resume-form").addEventListener("change", (e) => {
    const el = e.target;
    if (el.dataset.docLang === undefined) return;
    const from = docLang, to = el.value;
    if (to === from) return;
    /* `data.lang` was already set by the generic input handler above - a select
       fires `input` before `change` - so this only has to do the rest. */
    setPath(data, "lang", to);

    /* OFFERED, not done silently: a level word is user content that gets
       printed on the page. Declining is a valid answer - `LEVEL_DOTS` maps both
       vocabularies, so an English "Expert" in an Arabic résumé still draws five
       dots; it just reads in Latin. Only asked when there is something to
       translate. */
    const plan = levelRemapPlan(from, to);
    if (plan.length) {
      const q = T("Translate the level words already chosen? ") +
        plan.length + " (" + plan[0].from + " → " + plan[0].to + ")";
      if (window.confirm(q)) plan.forEach((c) => setPath(data, c.path, c.to));
    }

    docLang = to;
    applyLevelVocab(to);   // the dropdowns re-offer the new language's words
    onChange(true);        // re-render form, preview and save
  });

  /* ---------- preview ---------- */
  const frame = $("#preview-frame");
  const stage = $("#preview-stage");
  const scroll = $("#preview-scroll");
  let zoom = "fit";

  async function doRender() {
    try {
      const res = await fetch(EP.render, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data: stripPrivate(data), template_key: templateKey }),
      });
      if (res.status === 422) {
        const j = await res.json();
        showErrors(j.errors || [T("Invalid résumé data.")]);
        return;
      }
      /* Anything else non-OK is the server failing, not the network. The old
         code fell through to `res.json()`, which throws on an HTML error page,
         and the catch below then blamed the connection — a 500 reported itself
         as "could not reach", which is exactly the wrong place to look. */
      if (!res.ok) {
        showErrors([T("The preview could not be built (server error ") + res.status + ")."]);
        return;
      }
      showErrors(null);
      const j = await res.json();
      frame.srcdoc = j.doc;
      frame.onload = checkOverflow;
    } catch (_) {
      showErrors([T("Could not reach the preview service.")]);
    }
  }

  /* The document auto-fits itself (app/static/js/autofit.js) once its fonts
     have loaded; we just report the outcome. Three states:
       fitted at full spacing -> nothing to say
       fitted after compression -> an info note, so the user knows the layout
                                   was tightened and can trim if they'd rather
       still over at the floor -> the warning, as before
     Reading `.tpl.scrollHeight` directly is not equivalent: absolutely-placed
     panels never grow it, so it under-reports on 7 of the Modern layouts. */
  function checkOverflow() {
    const warn = $("#page-warn");
    warn.hidden = true;
    let win;
    try { win = frame.contentWindow; } catch (_) { return; }
    if (!win || !win.ResumeAutofit) return;
    win.ResumeAutofit.ready.then((r) => {
      if (!r || r.error) return;
      if (!r.fitted) {
        warn.classList.remove("is-info");
        warn.textContent =
          T("Content still runs past one page after auto-fit — trim it, or pick a denser layout.");
        warn.hidden = false;
      } else if (r.compressed) {
        warn.classList.add("is-info");
        warn.textContent =
          T("Auto-fitted to one page — spacing tightened ") +
          Math.round((1 - r.density) * 100) + "%.";
        warn.hidden = false;
      }
    }).catch(() => {});
  }

  function stripPrivate(o) {
    const c = JSON.parse(JSON.stringify(o));
    Object.keys(c).forEach((k) => { if (k.startsWith("_")) delete c[k]; });
    return c;
  }

  function showErrors(list) {
    const box = $("#form-errors");
    if (!list || !list.length) { box.classList.remove("show"); box.textContent = ""; return; }
    box.textContent = T("Fix to update preview:") + "\n• " + list.join("\n• ");
    box.classList.add("show");
  }

  function applyZoom() {
    const avail = scroll.clientWidth - 64;
    let scale;
    if (zoom === "fit") scale = Math.min(1, avail / 850);
    else scale = zoom;
    stage.style.transform = `scale(${scale})`;
    stage.style.marginBottom = `${(scale - 1) * 1100}px`;
    $("#zoom-lvl").textContent = zoom === "fit" ? T("Fit") : Math.round(scale * 100) + "%";
  }
  $$(".zoom button").forEach((b) => b.addEventListener("click", () => {
    const cur = zoom === "fit" ? Math.min(1, (scroll.clientWidth - 64) / 850) : zoom;
    if (b.dataset.zoom === "in") zoom = Math.min(1.5, cur + 0.1);
    else if (b.dataset.zoom === "out") zoom = Math.max(0.3, cur - 0.1);
    else zoom = "fit";
    applyZoom();
  }));
  window.addEventListener("resize", () => { if (zoom === "fit") applyZoom(); });

  /* ---------- save ---------- */
  function setSaveState(kind) {
    const el = $("#save-state");
    el.className = "save-state" + (kind === "unsaved" ? " is-unsaved" : kind === "saving" ? " is-saving" : "");
    el.textContent = kind === "unsaved" ? T("Unsaved changes") : kind === "saving" ? T("Saving…") : T("Saved");
  }
  /* The photo upload borrows the indicator, so it needs a way to give it back
     without lying: T("Saved") only if no edit is still waiting on the debounce. */
  function restoreSaveState() { setSaveState(savePending ? "unsaved" : "saved"); }

  async function doSave() {
    setSaveState("saving");
    const payload = JSON.stringify(stripPrivate(data));

    /* The browser IS the save. It happens first and it is what the indicator
       reports, because it is the copy the user gets back on their next visit.
       A storage failure is a real "unsaved" — say so rather than showing
       "Saved" over a résumé that will not survive a refresh. */
    if (!writeStored(STORE_KEY, payload)) {
      savePending = true;
      setSaveState("unsaved");
      return;
    }
    savePending = false;
    setSaveState("saved");

    /* Mirror to the server only where the server keeps a résumé at all: the
       local single-user workflow, and the browser suite built on it. On a
       deployment this is off and the route refuses anyway, so a stale page
       cannot write the shared file. Its outcome deliberately does NOT move
       the indicator — the save already succeeded where it counts, and a
       failed mirror reporting "unsaved" would be a lie that makes the user
       retype work they have not lost. */
    if (!S.serverStore) return;
    try {
      await fetch(EP.saveResume, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: payload,
      });
    } catch (_) { /* the local copy stands */ }
  }

  /* ---------- template drawer ---------- */
  const drawer = $("#drawer"), scrim = $("#drawer-scrim");
  /* Switching template is the only builder action with no feedback path of its
     own — the form has #form-errors, exports alert, saving has the indicator —
     and the scrim is over #form-errors while the drawer is open. So it gets
     its own line, cleared whenever the drawer is reopened. */
  function showDrawerError(msg) {
    const box = $("#drawer-error");
    box.textContent = msg || "";
    box.hidden = !msg;
  }
  /* ---------- drawer minis ----------
     Each mini shows YOUR résumé in that layout, deliberately: you are picking
     a layout for your own content, and stock text would be a lie about how it
     will look. That used to be an <iframe src="/preview?template_key=…">,
     which worked only because the server held the one résumé. It no longer
     does, so each mini is rendered from the document in this browser instead.

     Two things keep that affordable. Renders are lazy — an IntersectionObserver
     fills a mini when it is about to be seen, so opening the drawer costs the
     handful on screen and not all 49. And they are cached for as long as the
     drawer stays open, then dropped when it closes, because by the next time
     it opens the résumé has probably changed and a cached mini would be
     showing text the user has since edited. */
  const miniDocs = new Map();
  let miniObserver = null;

  async function fillMini(frame) {
    const key = frame.dataset.mini;
    if (!key || frame.dataset.filled) return;
    frame.dataset.filled = "1";
    if (miniDocs.has(key)) { frame.srcdoc = miniDocs.get(key); return; }
    try {
      const res = await fetch(EP.render, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data: stripPrivate(data), template_key: key }),
      });
      if (!res.ok) { delete frame.dataset.filled; return; }
      const j = await res.json();
      if (!j.ok) { delete frame.dataset.filled; return; }
      miniDocs.set(key, j.doc);
      frame.srcdoc = j.doc;
    } catch (_) {
      /* Leave the mini blank and let it retry on the next open. A failed
         thumbnail must not block choosing the template it belongs to. */
      delete frame.dataset.filled;
    }
  }

  function watchMinis() {
    if (miniObserver) miniObserver.disconnect();
    miniObserver = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) fillMini(e.target); });
    }, { root: $("#drawer-body"), rootMargin: "200px" });
    $$("#drawer-body iframe[data-mini]").forEach((f) => miniObserver.observe(f));
  }

  function openDrawer() {
    showDrawerError(null);
    drawer.classList.add("is-open"); scrim.classList.add("is-open");
    drawer.setAttribute("aria-hidden", "false");
    buildDrawer();
    /* The résumé may have changed since the drawer was last open, so every
       mini is stale until proven otherwise. */
    miniDocs.clear();
    $$("#drawer-body iframe[data-mini]").forEach((f) => { delete f.dataset.filled; f.removeAttribute("srcdoc"); });
    watchMinis();
  }
  function closeDrawer() { drawer.classList.remove("is-open"); scrim.classList.remove("is-open"); drawer.setAttribute("aria-hidden", "true"); }
  $("#open-drawer").addEventListener("click", openDrawer);
  $("#close-drawer").addEventListener("click", closeDrawer);
  scrim.addEventListener("click", closeDrawer);

  function buildDrawer() {
    const body = $("#drawer-body");
    if (body.dataset.built) { markCurrent(); return; }
    const groups = { modern: [], ats: [] };
    catalogue.forEach((t) => groups[t.category].push(t));
    let html = "";
    [["modern", T("Modern")], ["ats", T("ATS-Friendly")]].forEach(([cat, label]) => {
      html += `<div class="grp-label">${label}</div>`;
      groups[cat].forEach((t) => {
        html += `<div class="drawer-item${t.key === templateKey ? " is-current" : ""}" data-key="${t.key}" ${t.ported ? "" : 'aria-disabled="true"'}>
          <div class="mini">${t.ported ? `<iframe data-mini="${t.key}" title="" scrolling="no"></iframe>` : ""}</div>
          <div class="info"><b>${esc(T(t.label))}</b><p>${esc(T(t.blurb))}</p>${t.ported ? "" : `<p style="color:var(--warn)">${T("Coming soon")}</p>`}</div>
        </div>`;
      });
    });
    body.innerHTML = html;
    body.dataset.built = "1";
    body.addEventListener("click", async (e) => {
      const item = e.target.closest(".drawer-item");
      if (!item || item.getAttribute("aria-disabled") === "true") return;
      const key = item.dataset.key;
      /* This used to end a failure with a bare `if (!res.ok) return;`, and had
         no catch at all around the fetch. Either way the drawer stayed open,
         the layout did not change and nothing was said — a failed switch was
         indistinguishable from clicking the template already selected, and a
         dropped connection became an unhandled rejection in the console. */
      /* The choice is the browser's, like the résumé. It is stored before
         anything is asked of the server, so a switch cannot fail for a reason
         the user cannot act on. */
      if (!writeStored(TPL_KEY, key)) {
        showDrawerError(T("The template could not be switched — this browser is not storing anything."));
        return;
      }
      showDrawerError(null);
      if (S.serverStore) {
        /* Mirror, for the local workflow. A failure here is not the user's
           problem: the switch has already happened. */
        try {
          await fetch(EP.setTemplate, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ template_key: key }),
          });
        } catch (_) { /* the local choice stands */ }
      }
      templateKey = key;
      const t = catalogue.find((x) => x.key === key);
      $("#tpl-label").textContent = T(t.label);
      /* The chip's COLOUR was being swapped without its TEXT, so switching a
         Modern template for an ATS one left the bar reading "Modern" in an ATS
         colour until the page was reloaded. `lastChild` is the bare text node -
         textContent on the chip itself would delete the `.dot` span. */
      const chip = $(".builder-bar .tpl-name .chip");
      chip.className = "chip chip-" + t.category;
      chip.lastChild.textContent = t.category === "modern" ? T("Modern") : T("ATS");
      markCurrent();
      closeDrawer();
      doRender();
    });
  }
  function markCurrent() {
    $$("#drawer-body .drawer-item").forEach((n) => n.classList.toggle("is-current", n.dataset.key === templateKey));
  }

  /* ---------- download menu ---------- */
  const dlMenu = $("#dl-menu");
  $("#dl-toggle").addEventListener("click", (e) => { e.stopPropagation(); dlMenu.classList.toggle("is-open"); });
  document.addEventListener("click", () => dlMenu.classList.remove("is-open"));
  async function download(kind, url) {
    dlMenu.classList.remove("is-open");
    await doSave();
    /* POST the document rather than saving it and asking the server to export
       "the" résumé. The old flow only worked because there was exactly one:
       with two visitors, the GET could hand you a PDF of somebody else's CV.
       Sending it also means the export always matches what is on screen —
       there is no window between the save and the read for them to disagree. */
    try {
      const res = await fetch(url, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data: stripPrivate(data), template_key: templateKey }),
      });
      if (!res.ok) {
        const txt = await res.text();
        alert(kind + T(" export failed.") + "\n\n" + txt.replace(/<[^>]+>/g, "").trim().slice(0, 300));
        return;
      }
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = (data.name || "resume").replace(/[^\w\-]+/g, "_").toLowerCase() + (kind === "PDF" ? ".pdf" : ".docx");
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    } catch (_) {
      alert(T("Could not download the ") + kind + " file.");
    }
  }
  $("#dl-pdf").addEventListener("click", (e) => { e.preventDefault(); download("PDF", EP.pdf); });
  $("#dl-docx").addEventListener("click", (e) => { e.preventDefault(); download("Word", EP.docx); });

  /* ---------- boot ---------- */
  renderForm();
  applyZoom();
  doRender();
  setSaveState("saved");
})();
