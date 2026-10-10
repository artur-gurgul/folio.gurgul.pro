// site.js — the side panel. A page's HTML is its own content only, in plain
// <main> (layouts/default.pug, memos.pug); everything around it is built here.
//
// The order is the owner's (2026-10-10): "content, the folio, loads first …
// then it fetches css and js, and once js is loaded then it fetches json files
// … and adds menus and dynamic content". So, when this deferred file runs:
//   1. at once, the panel's fixed part — what does not depend on the site's
//      contents: the site's name (a link to the front page), its tagline, and
//      the filter's fold — as <aside class="sidebar"> before <main>;
//   2. then, from the one file Sajt writes for it (generate.nav, the body's
//      data-nav):
//      * "Contents" — the pages in the menu, grouped by top-level folder, when
//        the site has any;
//      * the filter (owner, 2026-09-26: "tag area and selection should be done
//        on the side panel, also search should be there"): a search box — a GET
//        form to the folio list, so it works on every page — and the areas with
//        their counts; the current folio's area (the body's data-area), or "all
//        areas" on the list itself, is marked.
//      No tags in the panel (owner, 2026-09-29: "tags on the side bar are
//      broken, remove them from sidebar") — a folio's tags are its chip bar.
// The content never moves when the panel arrives: with JavaScript on, the CSS
// keeps the panel's place from the first paint (all.css, "scripting"). On a
// phone the panel sits above the content, folded to one line.
// On the list page, static/js/memos.js takes the filter over; it waits for it
// through window.folioPanel, a promise of the <form class="side-filter">
// (rejected when the panel could not be built — the list then stays whole).
// Nothing is fetched from anywhere but the site's own files.
(function () {
  "use strict"

  var SITE = "folio"
  var TAGLINE = "one subject, one A4 page"
  var PHONE = "(max-width: 860px)"   // all.css's phone breakpoint

  var settle = {}
  window.folioPanel = new Promise(function (resolve, reject) {
    settle.resolve = resolve
    settle.reject = reject
  })
  // memos.js handles a rejection; nobody else needs to hear of it
  window.folioPanel.catch(function () {})

  /// An element with attributes (null/undefined ones skipped) and children
  /// (strings become text — nothing from the JSON is ever parsed as HTML).
  function el(tag, attrs, children) {
    var node = document.createElement(tag)
    for (var key in attrs || {}) {
      if (attrs[key] !== null && attrs[key] !== undefined) {
        node.setAttribute(key, attrs[key])
      }
    }
    (children || []).forEach(function (child) {
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child)
    })
    return node
  }

  var SVG = "http://www.w3.org/2000/svg"

  /// The fold's chevron, drawn on a phone where the fold is a real toggle.
  function chevron() {
    var svg = document.createElementNS(SVG, "svg")
    svg.setAttribute("class", "chevron")
    svg.setAttribute("viewBox", "0 0 16 16")
    svg.setAttribute("width", "14")
    svg.setAttribute("height", "14")
    svg.setAttribute("aria-hidden", "true")
    var path = document.createElementNS(SVG, "path")
    path.setAttribute("d", "M4 6l4 4 4-4")
    path.setAttribute("fill", "none")
    path.setAttribute("stroke", "currentColor")
    path.setAttribute("stroke-width", "1.8")
    path.setAttribute("stroke-linecap", "round")
    path.setAttribute("stroke-linejoin", "round")
    svg.appendChild(path)
    return svg
  }

  var body = document.body
  var main = document.querySelector("main")
  var phone = !!(window.matchMedia && matchMedia(PHONE).matches)
  if (!main) {
    settle.reject(new Error("site.js: no <main> on this page"))
    return
  }

  // 1. the fixed part, before anything is fetched
  // `contents` on the fold too: it folds on a phone like the contents do
  var fold = el("details", { "class": "contents side-fold", open: phone ? null : "" }, [
    el("summary", null, [el("span", { "class": "contents-label side-fold-label" }, ["Filter"]), chevron()])
  ])
  var nav = el("nav", { "class": "site-nav" }, [
    el("h2", { "class": "intro" }, [el("a", { href: "/" }, [SITE])]),
    el("p", { "class": "tagline" }, [TAGLINE]),
    fold
  ])
  body.insertBefore(el("aside", { "class": "sidebar" }, [nav]), main)
  document.documentElement.classList.add("has-panel")

  var navUrl = body.getAttribute("data-nav")
  if (!navUrl || !window.fetch) {
    fold.parentNode.removeChild(fold)
    settle.reject(new Error("site.js: this page names no nav.json"))
    return
  }

  /// The page as Sajt names it: /dir/name.html. GitHub Pages also serves
  /// /dir/name and /dir/ (for index.html).
  function pagePath() {
    var path = location.pathname
    if (/\/$/.test(path)) {
      return path + "index.html"
    }
    return /\.[a-z0-9]+$/i.test(path) ? path : path + ".html"
  }

  function contents(menu, here) {
    var groups = []
    menu.forEach(function (item) {
      var segments = item.url.split("/").filter(Boolean)
      var key = segments.length > 1 ? segments[0] : ""
      var group = groups.filter(function (g) { return g.key === key })[0]
      if (!group) {
        group = { key: key, items: [] }
        groups.push(group)
      }
      group.items.push(item)
    })
    var details = el("details", { "class": "contents", open: "" }, [
      el("summary", null, [el("span", { "class": "contents-label" }, ["Contents"]), chevron()])
    ])
    groups.forEach(function (group) {
      if (group.key) {
        details.appendChild(el("p", { "class": "group" }, [group.key]))
      }
      details.appendChild(el("ul", { "class": "posts" }, group.items.map(function (item) {
        var current = item.url === here
        return el("li", null, [el("a", {
          href: item.url,
          "class": current ? "current" : null,
          "aria-current": current ? "page" : null
        }, [item.title])])
      })))
    })
    return details
  }

  function filter(memos, here) {
    var area = body.getAttribute("data-area") || ""
    var onList = here === memos.list
    function item(label, key, count, href, current) {
      return el("li", null, [el("a", {
        "class": "side-area" + (current ? " current" : ""),
        href: href,
        "data-area": key,
        "aria-current": current ? "page" : null
      }, [label, el("span", { "class": "count" }, [String(count)])])])
    }
    var areas = el("ul", { "class": "posts side-areas" }, [item("all areas", "", memos.count, memos.list, onList)])
    memos.areas.forEach(function (a) {
      areas.appendChild(item(a.key, a.key, a.count, memos.list + "?area=" + encodeURIComponent(a.key), a.key === area))
    })
    return el("form", { "class": "side-filter", action: memos.list, method: "get", "data-list": memos.list }, [
      el("input", {
        "class": "side-search", type: "search", name: "q", placeholder: "search the folios…",
        "aria-label": "Search the folios", autocomplete: "off"
      }),
      el("p", { "class": "group" }, ["Area"]),
      areas
    ])
  }

  fetch(navUrl).then(function (response) {
    if (!response.ok) {
      throw new Error("site.js: " + navUrl + " answered " + response.status)
    }
    return response.json()
  }).then(function (data) {
    var here = pagePath()
    if (data.menu && data.menu.length) {
      var list = contents(data.menu, here)
      list.open = !phone
      nav.insertBefore(list, fold)
    }
    if (!data.memos) {
      fold.parentNode.removeChild(fold)
      throw new Error("site.js: nav.json has no folio list")
    }
    var form = filter(data.memos, here)
    fold.appendChild(form)
    settle.resolve(form)
  }).catch(function (error) {
    settle.reject(error)
    if (window.console) {
      console.warn(error)
    }
  })
})()
