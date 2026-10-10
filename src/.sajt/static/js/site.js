// site.js — the side panel, built from nav.json after the content is on screen.
//
// A page's HTML carries its own content only (layouts/frame.pug). By the time
// this deferred file runs, the inline script in the page has already made that
// content the page, beside the panel's fixed part (layouts/sidebar.pug). This
// fills the rest from the one file Sajt writes for it (generate.nav, the
// body's data-nav):
//   * "Contents" — the pages in the menu, grouped by top-level folder, when the
//     site has any;
//   * the filter: a search box — a GET form to the folio list, so it works on
//     every page — and the areas with their counts; the current folio's area
//     (the body's data-area), or "all areas" on the list itself, is marked.
// On the list page, static/js/memos.js takes the filter over; it waits for it
// through window.folioPanel, a promise of the <form class="side-filter">
// (rejected when the panel could not be built — the list then stays whole).
// Nothing is fetched from anywhere but the site's own files.
(function () {
  "use strict"

  var settle = {}
  window.folioPanel = new Promise(function (resolve, reject) {
    settle.resolve = resolve
    settle.reject = reject
  })
  // memos.js handles a rejection; nobody else needs to hear of it
  window.folioPanel.catch(function () {})

  var body = document.body
  var navUrl = body.getAttribute("data-nav")
  var nav = document.querySelector(".sidebar .site-nav")
  if (!navUrl || !nav || !window.fetch) {
    settle.reject(new Error("site.js: no nav.json or no side panel on this page"))
    return
  }

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

  /// The page as Sajt names it: /dir/name.html. GitHub Pages also serves
  /// /dir/name and /dir/ (for index.html).
  function pagePath() {
    var path = location.pathname
    if (/\/$/.test(path)) {
      return path + "index.html"
    }
    return /\.[a-z0-9]+$/i.test(path) ? path : path + ".html"
  }

  function contents(menu, here, chevron) {
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
      el("summary", null, [el("span", { "class": "contents-label" }, ["Contents"]), chevron.cloneNode(true)])
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
    var fold = nav.querySelector("details.side-fold")
    var chevron = nav.querySelector("svg.chevron")
    var phone = window.matchMedia && matchMedia("(max-width: 860px)").matches
    if (data.menu && data.menu.length && chevron) {
      var list = contents(data.menu, here, chevron)
      list.open = !phone
      nav.insertBefore(list, fold)
    }
    if (!data.memos || !fold) {
      if (fold) {
        fold.parentNode.removeChild(fold)
      }
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
