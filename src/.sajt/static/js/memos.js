// memos.js — the memo list, filtered from the side panel.
//
// The sidebar (layouts/sidebar.pug) holds the filter: a search box and the
// areas — plain links and a GET form into the memo list, so the page works
// with this file absent. On the list page this script takes those controls
// over:
//   * a click on an area filters in place (one area at a time), typing
//     searches;
//   * tags are NOT in the sidebar (owner, 2026-09-29: "tags on the side bar
//     are broken, remove them from sidebar"); a tag filter still arrives in
//     the URL from a sheet's own chip bar (?tag=actors) and is honoured;
//   * the search reads the sheets' text (data-search → search.json, fetched
//     the first time the box is used);
//   * the state lives in the URL (?area=swift&tag=actors&q=reentrancy), so a
//     filter is a link and the browser's back button undoes a step.
// Nothing is fetched from anywhere but the site's own files.
(function () {
  "use strict"

  var root = document.querySelector(".memos")
  var panel = document.querySelector(".side-filter")
  if (!root || !panel || !window.fetch) {
    return
  }
  var LABEL_KEYS = ["topic", "platform", "level", "kind"]

  var search = null            // url → lowercased text
  var state = { area: "", labels: {}, tags: [], q: "" }
  var items = Array.prototype.slice.call(root.querySelectorAll(".memos-list > li"))
  var areas = Array.prototype.slice.call(root.querySelectorAll(".memos-area"))
  var count = root.querySelector(".memos-count")
  var active = root.querySelector(".memos-active")
  var empty = root.querySelector(".memos-empty")

  var searchBox = panel.querySelector(".side-search")
  var selects = {}
  LABEL_KEYS.forEach(function (key) {
    selects[key] = panel.querySelector('select[name="' + key + '"]')
  })

  // ── state ↔ URL ──────────────────────────────────────────────────────────

  function readURL() {
    var params = new URLSearchParams(location.search)
    state = { area: params.get("area") || "", labels: {}, tags: [], q: (params.get("q") || "").trim() }
    LABEL_KEYS.forEach(function (key) {
      var values = params.getAll(key).filter(Boolean)
      if (values.length) {
        state.labels[key] = values
      }
    })
    state.tags = params.getAll("tag").filter(Boolean)
  }

  function writeURL() {
    var params = new URLSearchParams()
    if (state.area) {
      params.set("area", state.area)
    }
    LABEL_KEYS.forEach(function (key) {
      (state.labels[key] || []).forEach(function (v) { params.append(key, v) })
    })
    state.tags.forEach(function (t) { params.append("tag", t) })
    if (state.q) {
      params.set("q", state.q)
    }
    var query = params.toString()
    history.replaceState(null, "", location.pathname + (query ? "?" + query : ""))
  }

  // ── filtering ────────────────────────────────────────────────────────────

  function itemTags(li) {
    return (li.getAttribute("data-tags") || "").split(/\s+/).filter(Boolean)
  }

  /// Does the sheet match the area, the labels, the tags and the search?
  function itemMatches(li) {
    if (state.area && li.getAttribute("data-area") !== state.area) {
      return false
    }
    var labels = (li.getAttribute("data-labels") || "").split(/\s+/)
    for (var key in state.labels) {
      var ok = state.labels[key].some(function (v) { return labels.indexOf(key + "=" + v) >= 0 })
      if (!ok) {
        return false
      }
    }
    var tags = itemTags(li)
    for (var i = 0; i < state.tags.length; i++) {
      if (tags.indexOf(state.tags[i]) < 0) {
        return false
      }
    }
    if (state.q) {
      var url = li.getAttribute("data-url")
      var hay = li.textContent.toLowerCase() + " " + (search && search[url] ? search[url] : "")
      var words = state.q.toLowerCase().split(/\s+/).filter(Boolean)
      for (var w = 0; w < words.length; w++) {
        if (hay.indexOf(words[w]) < 0) {
          return false
        }
      }
    }
    return true
  }

  function describe() {
    var parts = []
    if (state.area) {
      parts.push("area " + state.area)
    }
    LABEL_KEYS.forEach(function (key) {
      (state.labels[key] || []).forEach(function (v) { parts.push(key + " " + v) })
    })
    state.tags.forEach(function (t) { parts.push("#" + t) })
    if (state.q) {
      parts.push("“" + state.q + "”")
    }
    return parts.length ? " · " + parts.join(" · ") : ""
  }

  function apply() {
    var shown = 0
    items.forEach(function (li) {
      var on = itemMatches(li)
      li.classList.toggle("hidden", !on)
      if (on) {
        shown++
      }
    })
    areas.forEach(function (area) {
      area.classList.toggle("hidden", !area.querySelector(".memos-list > li:not(.hidden)"))
    })
    var noun = items.length === 1 ? " folio" : " folios"
    count.textContent = shown === items.length ? items.length + noun : shown + " of " + items.length + noun
    active.textContent = describe()
    empty.classList.toggle("hidden", shown > 0)
    syncPanel()
    writeURL()
  }

  // ── the side panel ───────────────────────────────────────────────────────

  function syncPanel() {
    panel.querySelectorAll(".side-area").forEach(function (a) {
      var on = (a.getAttribute("data-area") || "") === state.area
      // the static page marks "all areas" as the current page; here the
      // selection is the only highlight
      a.classList.remove("current")
      a.classList.toggle("on", on)
      a.setAttribute("aria-current", on ? "true" : "false")
    })
    LABEL_KEYS.forEach(function (key) {
      // the theme ships no category selects (owner, 2026-09-26); a label
      // filter still works from the URL, and a select is honoured if a site
      // adds one to its sidebar
      if (!selects[key]) {
        return
      }
      var values = state.labels[key] || []
      selects[key].value = values.length ? values[0] : ""
      selects[key].classList.toggle("on", values.length > 0)
    })
    if (searchBox.value.trim() !== state.q) {
      searchBox.value = state.q
    }
  }

  function loadSearch() {
    if (search !== null) {
      return
    }
    search = {}
    fetch(root.getAttribute("data-search")).then(function (r) { return r.json() }).then(function (data) {
      data.sheets.forEach(function (s) { search[s.url] = (s.text || "").toLowerCase() })
      if (state.q) {
        apply()
      }
    }).catch(function () {})
  }

  // ── wiring ───────────────────────────────────────────────────────────────

  panel.addEventListener("click", function (event) {
    var a = event.target.closest("a.side-area")
    if (!a) {
      return
    }
    event.preventDefault()
    var area = a.getAttribute("data-area") || ""
    state.area = state.area === area ? "" : area
    // a new area: a tag that arrived in the URL and no sheet of this area
    // carries no longer applies
    if (state.area) {
      state.tags = state.tags.filter(function (t) {
        return items.some(function (li) {
          return li.getAttribute("data-area") === state.area && itemTags(li).indexOf(t) >= 0
        })
      })
    }
    apply()
  })

  panel.addEventListener("submit", function (event) {
    event.preventDefault()
    state.q = searchBox.value.trim()
    apply()
  })

  LABEL_KEYS.forEach(function (key) {
    if (!selects[key]) {
      return
    }
    selects[key].addEventListener("change", function () {
      if (selects[key].value) {
        state.labels[key] = [selects[key].value]
      } else {
        delete state.labels[key]
      }
      apply()
    })
  })

  var timer = null
  searchBox.addEventListener("input", function () {
    loadSearch()
    clearTimeout(timer)
    timer = setTimeout(function () {
      state.q = searchBox.value.trim()
      apply()
    }, 120)
  })
  searchBox.addEventListener("focus", loadSearch)

  window.addEventListener("popstate", function () {
    readURL()
    apply()
  })

  readURL()
  apply()
  if (state.q) {
    loadSearch()
  }
})()
