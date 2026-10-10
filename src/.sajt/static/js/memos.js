// memos.js — the folio list, filtered from the side panel.
//
// The list page's HTML holds the list itself — each folio's title and
// one-liner, grouped by area (layouts/memos.pug) — and nothing that only the
// filter needs. This file adds that, after the list is on screen:
//   * each folio's area (from its section), and from the index Sajt writes
//     (data-index → index.json) its labels and tags — the tag links under
//     each folio are drawn from there;
//   * the filter, in the side panel that site.js builds from nav.json
//     (window.folioPanel): a click on an area filters in place (one area at a
//     time), typing searches the folios' text (data-search → search.json,
//     fetched the first time the box is used);
//   * tags are NOT in the side panel (owner, 2026-09-29: "tags on the side bar
//     are broken, remove them from sidebar"); a tag filter arrives in the URL
//     from a folio's chip bar or a tag link here (?tag=actors) and is honoured;
//   * the state lives in the URL (?area=swift&tag=actors&q=reentrancy), so a
//     filter is a link and the browser's back button undoes a step.
// An area in the URL filters at once; a tag or label filter waits for the
// index (until then the whole list shows). Nothing is fetched from anywhere but
// the site's own files.
(function () {
  "use strict"

  var root = document.querySelector(".memos")
  if (!root || !window.fetch) {
    return
  }
  var LABEL_KEYS = ["topic", "platform", "level", "kind"]
  var list = root.getAttribute("data-list") || location.pathname

  var search = null            // url → lowercased text
  var indexed = false          // labels and tags known
  var state = { area: "", labels: {}, tags: [], q: "" }
  var items = Array.prototype.slice.call(root.querySelectorAll(".memos-list > li"))
  var areas = Array.prototype.slice.call(root.querySelectorAll(".memos-area"))
  var count = root.querySelector(".memos-count")
  var active = root.querySelector(".memos-active")
  var empty = document.createElement("p")
  empty.className = "memos-empty hidden"
  empty.textContent = "Nothing matches — clear a filter in the side panel."
  root.appendChild(empty)

  var panel = null             // the side panel's <form>, once site.js has built it
  var searchBox = null
  var selects = {}

  // what the page itself says: the URL of each folio, the area of its section
  areas.forEach(function (section) {
    section.querySelectorAll(".memos-list > li").forEach(function (li) {
      li.setAttribute("data-area", section.getAttribute("data-area") || "")
    })
  })
  items.forEach(function (li) {
    var a = li.querySelector("a.memos-title")
    li.setAttribute("data-url", a ? a.getAttribute("href") : "")
  })

  // ── the index: labels and tags ───────────────────────────────────────────

  function enrich(index) {
    var byUrl = {}
    index.sheets.forEach(function (s) { byUrl[s.url] = s })
    items.forEach(function (li) {
      var sheet = byUrl[li.getAttribute("data-url")]
      if (!sheet) {
        return
      }
      var labels = []
      Object.keys(sheet.labels || {}).forEach(function (key) {
        sheet.labels[key].forEach(function (value) { labels.push(key + "=" + value) })
      })
      li.setAttribute("data-labels", labels.join(" "))
      li.setAttribute("data-tags", (sheet.tags || []).join(" "))
      if (sheet.tags && sheet.tags.length && !li.querySelector(".memos-tags")) {
        var p = document.createElement("p")
        p.className = "memos-tags"
        sheet.tags.forEach(function (tag, i) {
          if (i > 0) {
            p.appendChild(document.createTextNode(" · "))
          }
          var a = document.createElement("a")
          a.href = list + "?tag=" + encodeURIComponent(tag)
          a.textContent = tag
          p.appendChild(a)
        })
        li.appendChild(p)
      }
    })
    indexed = true
  }

  var indexReady = fetch(root.getAttribute("data-index")).then(function (response) {
    if (!response.ok) {
      throw new Error("memos.js: the index answered " + response.status)
    }
    return response.json()
  }).then(enrich).catch(function (error) {
    if (window.console) {
      console.warn(error)
    }
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

  /// A tag or label filter cannot be judged before the index has arrived.
  function needsIndex() {
    return state.tags.length > 0 || Object.keys(state.labels).length > 0
  }

  /// Does the folio match the area, the labels, the tags and the search?
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
    if (needsIndex() && !indexed) {
      return
    }
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
    if (!panel) {
      return
    }
    panel.querySelectorAll(".side-area").forEach(function (a) {
      var on = (a.getAttribute("data-area") || "") === state.area
      // the panel marks "all areas" as the current page; here the
      // selection is the only highlight
      a.classList.remove("current")
      a.classList.toggle("on", on)
      a.setAttribute("aria-current", on ? "true" : "false")
    })
    LABEL_KEYS.forEach(function (key) {
      // the theme ships no category selects (owner, 2026-09-26); a label
      // filter still works from the URL, and a select is honoured if a site
      // adds one to its panel
      if (!selects[key]) {
        return
      }
      var values = state.labels[key] || []
      selects[key].value = values.length ? values[0] : ""
      selects[key].classList.toggle("on", values.length > 0)
    })
    if (searchBox && searchBox.value.trim() !== state.q) {
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

  function wire(form) {
    panel = form
    searchBox = panel.querySelector(".side-search")
    LABEL_KEYS.forEach(function (key) {
      selects[key] = panel.querySelector('select[name="' + key + '"]')
    })

    panel.addEventListener("click", function (event) {
      var a = event.target.closest("a.side-area")
      if (!a) {
        return
      }
      event.preventDefault()
      var area = a.getAttribute("data-area") || ""
      state.area = state.area === area ? "" : area
      // a new area: a tag that arrived in the URL and no folio of this area
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
    syncPanel()
  }

  // ── wiring ───────────────────────────────────────────────────────────────

  window.addEventListener("popstate", function () {
    readURL()
    apply()
  })

  readURL()
  apply()
  if (state.q) {
    loadSearch()
  }
  indexReady.then(apply)
  if (window.folioPanel) {
    window.folioPanel.then(wire, function () {})
  }
})()
