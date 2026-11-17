// The try-it page: loads Pyodide, unpacks the kit and calls the bridge module trykit.py.
// All output is inserted as text, never as HTML.
"use strict";

const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.29.5/full/";
const $ = (id) => document.getElementById(id);
let kit = null;
let examples = { build: [], import: [], meta: {} };
let lastBundle = null;

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  for (const child of children) node.append(child);
  return node;
}

function setStatus(text, state) {
  const box = $("loading");
  $("loading-text").textContent = text;
  box.dataset.state = state;
}

async function start() {
  try {
    const [pyodide, zip, ex] = await Promise.all([
      loadPyodide({ indexURL: PYODIDE_URL }),
      fetch("diga_epa_kit.zip").then((r) => { if (!r.ok) throw new Error("diga_epa_kit.zip not found"); return r.arrayBuffer(); }),
      fetch("examples.json").then((r) => { if (!r.ok) throw new Error("examples.json not found"); return r.json(); }),
    ]);
    examples = ex;
    setStatus("Loading pydantic…", "loading");
    await pyodide.loadPackage("pydantic");
    pyodide.unpackArchive(zip, "zip", { extractDir: "/home/pyodide/kit" });
    pyodide.runPython("import sys; sys.path.insert(0, '/home/pyodide/kit')");
    kit = pyodide.pyimport("trykit");
    fillExamples();
    $("build-run").disabled = false;
    $("import-run").disabled = false;
    const meta = examples.meta || {};
    $("version").textContent = `kit version ${meta.kit_version || "?"} (${meta.git_rev || "?"})`;
    setStatus("Ready. Pick an example or paste your own input.", "ready");
  } catch (error) {
    setStatus(`The kit could not be loaded: ${error.message}. Reload the page; if it persists, your browser may block WebAssembly.`, "error");
  }
}

function fillExamples() {
  const select = $("example");
  select.replaceChildren(...examples.build.map((ex, i) => el("option", { value: String(i) }, ex.label)));
  showExample(0);
  if (examples.import.length) $("import-input").value = JSON.stringify(examples.import[0].data, null, 2);
}

function showExample(index) {
  const ex = examples.build[index];
  if (ex) $("build-input").value = JSON.stringify(ex.data, null, 2);
}

function errorList(errors) {
  return el("ul", { class: "errors" }, ...errors.map((e) => el("li", {}, el("code", {}, e.where), " ", e.message)));
}

function download(name, text) {
  const url = URL.createObjectURL(new Blob([text], { type: "application/fhir+json" }));
  const a = el("a", { href: url, download: name });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function codeBlock(text, label) {
  const pre = el("pre", { class: "code", tabindex: "0", "aria-label": label });
  pre.textContent = text;
  return pre;
}

function runBuild() {
  const out = $("build-result");
  out.classList.remove("empty");
  let result;
  try {
    result = JSON.parse(kit.build($("build-input").value));
  } catch (error) {
    out.replaceChildren(el("p", { class: "bad" }, `Unexpected error: ${error.message}`));
    return;
  }
  if (result.stage === "json") {
    out.replaceChildren(el("p", { class: "bad" }, "This is not valid JSON."), errorList(result.errors));
    return;
  }
  if (result.stage === "input") {
    out.replaceChildren(
      el("p", { class: "bad" }, `The input was rejected: ${result.errors.length} problem${result.errors.length === 1 ? "" : "s"}. Nothing was exported.`),
      errorList(result.errors),
    );
    return;
  }
  lastBundle = JSON.stringify(result.bundle, null, 2);
  const s = result.summary;
  const verdict = result.problems.length
    ? el("p", { class: "bad" }, "The kit's local checks found problems:")
    : el("p", { class: "good" }, `Bundle built: ${s.resources} resources. The kit's local checks found no problem.`);
  const profiles = el("table", { class: "summary" },
    el("caption", {}, "Resources by MIO DiGA profile"),
    ...Object.entries(s.profiles).map(([name, n]) => el("tr", {}, el("td", {}, name.replaceAll("_", " ")), el("td", { class: "num" }, String(n)))));
  const sections = el("table", { class: "summary" },
    el("caption", {}, "Document sections"),
    ...s.sections.map((sec) => el("tr", {}, el("td", {}, sec.title), el("td", { class: "num" }, String(sec.entries)))));
  const dl = el("button", { class: "primary" }, "Download bundle");
  dl.addEventListener("click", () => download(`diga-bundle-${new Date().toISOString().slice(0, 19).replaceAll(":", "")}.json`, lastBundle));
  const details = el("details", {}, el("summary", {}, "Show the FHIR bundle"), codeBlock(lastBundle, "FHIR bundle"));
  out.replaceChildren(verdict, ...(result.problems.length ? [errorList(result.problems.map((p) => ({ where: "check", message: p })))] : []),
    el("div", { class: "row buttons" }, dl), el("div", { class: "tables" }, profiles, sections), details,
    el("p", { class: "hint" }, "Next: validate the downloaded bundle with the official HL7 validator (see below)."));
}

function runImport() {
  const out = $("import-result");
  out.classList.remove("empty");
  let result;
  try {
    result = JSON.parse(kit.import_medication_list($("import-input").value));
  } catch (error) {
    out.replaceChildren(el("p", { class: "bad" }, `Unexpected error: ${error.message}`));
    return;
  }
  if (result.stage !== "done") {
    out.replaceChildren(el("p", { class: "bad" }, "The list could not be read."), errorList(result.errors));
    return;
  }
  const parts = [el("p", { class: result.medications.length ? "good" : "bad" },
    `${result.medications.length} medication${result.medications.length === 1 ? "" : "s"} read, ${result.skipped.length} skipped.`)];
  if (result.skipped.length) parts.push(el("h3", {}, "Skipped"), errorList(result.skipped));
  if (result.notes.length) parts.push(el("h3", {}, "Notes"), errorList(result.notes));
  const fragment = JSON.stringify({ medications: result.medications }, null, 2);
  parts.push(el("h3", {}, "As kit input"), codeBlock(fragment, "Medications as kit input"));
  if (result.medications.length) {
    const use = el("button", { class: "primary" }, "Add to the build input");
    use.addEventListener("click", () => {
      try {
        const input = JSON.parse($("build-input").value);
        input.medications = result.medications;
        $("build-input").value = JSON.stringify(input, null, 2);
        selectTab("build");
        $("build-result").replaceChildren(el("p", { class: "hint" },
          "Medications added to the input. Press “Build bundle”. A medication that starts after the export period (period_end) is rejected, so adjust the period if needed."));
      } catch {
        $("build-result").replaceChildren(el("p", { class: "bad" }, "The build input is not valid JSON, so the medications could not be added."));
        selectTab("build");
      }
    });
    parts.push(el("div", { class: "row buttons" }, use));
  }
  out.replaceChildren(...parts);
}

function selectTab(name) {
  for (const tab of ["build", "import"]) {
    const on = tab === name;
    $(`tab-${tab}`).setAttribute("aria-selected", String(on));
    $(`tab-${tab}`).tabIndex = on ? 0 : -1;
    $(`panel-${tab}`).hidden = !on;
  }
}

function readFile(input, target) {
  const file = input.files[0];
  if (!file) return;
  file.text().then((text) => { $(target).value = text; input.value = ""; });
}

$("tab-build").addEventListener("click", () => selectTab("build"));
$("tab-import").addEventListener("click", () => selectTab("import"));
$("example").addEventListener("change", (e) => showExample(Number(e.target.value)));
$("build-run").addEventListener("click", runBuild);
$("import-run").addEventListener("click", runImport);
$("build-file").addEventListener("change", (e) => readFile(e.target, "build-input"));
$("import-file").addEventListener("change", (e) => readFile(e.target, "import-input"));
start();
