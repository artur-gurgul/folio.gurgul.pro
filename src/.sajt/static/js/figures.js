// figures.js — a figure the column is too narrow for opens bigger on a click.
//
// sheet.css shows every figure at one target scale (--fig-scale times the size
// it is drawn at), as far as the column has room. A figure drawn across the
// page stops at the column and its text stays smaller than the page's. The
// owner, 2026-10-11: "the onces that can not be bigger should be possible to
// click on it and make them gigger temporarly". So, on a folio page:
//   * a figure shown smaller than its target is marked .zoomable: a zoom-in
//     cursor, and an "enlarge" button in the image's top-right corner (owner,
//     2026-10-11: cursor + corner icon — a phone has no cursor). The button is
//     what Tab reaches and a screen reader announces; a click on the image
//     itself works too;
//   * it opens in a <dialog> over the whole window, on the page's background:
//     as large as the window allows (up to MAX_SCALE times its drawn size),
//     centred; where the window is narrower than the figure already is on the
//     page (a phone), at the target scale, and it pans;
//   * a click anywhere, Esc, or the close button puts it away; focus goes back
//     to where it was.
// The marks follow the window: widen it and a figure that now fits is no
// longer zoomable. Without JavaScript, or without <dialog>, the figures stay
// as sheet.css shows them, and nothing is added to the page.
(function () {
  "use strict"

  var MAX_SCALE = 3      // enlarged: at most 3x the drawn size
  var MARGIN = 16        // px of window kept around the enlarged figure
  var SLACK = 0.97       // shown at 97 % of the target counts as reaching it
  var INSET = 6          // px between the image's corner and the button

  var images = Array.prototype.slice.call(
    document.querySelectorAll(".content.folio-page .sheet-figure img"))
  if (!images.length || typeof HTMLDialogElement !== "function") {
    return
  }

  var SVG = "http://www.w3.org/2000/svg"

  /// Two arrows apart, corner to corner: "make this bigger".
  function expandIcon() {
    var svg = document.createElementNS(SVG, "svg")
    svg.setAttribute("viewBox", "0 0 16 16")
    svg.setAttribute("width", "14")
    svg.setAttribute("height", "14")
    svg.setAttribute("aria-hidden", "true")
    var path = document.createElementNS(SVG, "path")
    path.setAttribute("d", "M9.5 2.5h4v4M13.5 2.5l-4.5 4.5M6.5 13.5h-4v-4M2.5 13.5l4.5-4.5")
    path.setAttribute("fill", "none")
    path.setAttribute("stroke", "currentColor")
    path.setAttribute("stroke-width", "1.6")
    path.setAttribute("stroke-linecap", "round")
    path.setAttribute("stroke-linejoin", "round")
    svg.appendChild(path)
    return svg
  }

  /// The target scale sheet.css uses (--fig-scale on :root).
  function targetScale() {
    var value = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--fig-scale"))
    return value > 0 ? value : 2.4
  }

  /// The size a figure is drawn at, in px (its width/height attributes).
  function drawn(img) {
    var w = parseFloat(img.getAttribute("width")) || img.naturalWidth || 0
    var h = parseFloat(img.getAttribute("height")) || img.naturalHeight || 0
    return { w: w, h: h }
  }

  /// The figure's "enlarge" button, made the first time it is needed.
  function hintOf(img, n) {
    var figure = img.parentNode
    var hint = figure.querySelector(".figure-zoom-hint")
    if (!hint) {
      hint = document.createElement("button")
      hint.type = "button"
      hint.className = "figure-zoom-hint"
      hint.setAttribute("aria-label", "Enlarge figure " + n)
      hint.setAttribute("title", "Enlarge")
      hint.appendChild(expandIcon())
      hint.addEventListener("click", function () {
        open(img)
      })
      figure.appendChild(hint)
    }
    return hint
  }

  /// Mark (or unmark) every figure the column stops short of its target, and
  /// put its button at the image's top-right corner — or, where the image is
  /// wider than its strip (a phone), at the strip's right edge.
  function mark() {
    var scale = targetScale()
    images.forEach(function (img, i) {
      var figure = img.parentNode
      var size = drawn(img)
      var short = size.w > 0 && img.getBoundingClientRect().width < size.w * scale * SLACK
      figure.classList.toggle("zoomable", short)
      var hint = figure.querySelector(".figure-zoom-hint")
      if (!short) {
        if (hint) {
          hint.hidden = true
        }
        return
      }
      hint = hintOf(img, i + 1)
      hint.hidden = false
      var right = Math.min(img.offsetLeft + img.offsetWidth, figure.clientWidth)
      hint.style.left = Math.round(right - hint.offsetWidth - INSET) + "px"
      hint.style.top = Math.round(img.offsetTop + INSET) + "px"
    })
  }

  var dialog = document.createElement("dialog")
  dialog.className = "figure-zoom"
  dialog.setAttribute("aria-label", "Enlarged figure")
  var close = document.createElement("button")
  close.type = "button"
  close.className = "figure-zoom-close"
  close.setAttribute("aria-label", "Close")
  close.appendChild(document.createTextNode("×"))
  var big = document.createElement("img")
  dialog.appendChild(close)
  dialog.appendChild(big)
  document.body.appendChild(dialog)

  /// The width to show a figure at: the window, up to MAX_SCALE; where the
  /// window is narrower than the figure already is on the page, the target
  /// scale (it pans).
  function enlarged(img) {
    var size = drawn(img)
    var roomW = document.documentElement.clientWidth - 2 * MARGIN
    var roomH = window.innerHeight - 2 * MARGIN
    var fit = Math.min(roomW, size.h > 0 ? roomH * size.w / size.h : roomW, size.w * MAX_SCALE)
    var shown = img.getBoundingClientRect().width
    if (fit > shown * 1.15) {
      return { width: fit, fits: true }
    }
    return { width: Math.max(size.w * targetScale(), shown), fits: false }
  }

  function open(img) {
    var size = enlarged(img)
    big.src = img.currentSrc || img.src
    big.alt = img.alt
    big.style.width = Math.round(size.width) + "px"
    dialog.classList.toggle("fits", size.fits)
    document.documentElement.classList.add("figure-zoom-open")
    dialog.showModal()
    dialog.scrollTop = 0
    dialog.scrollLeft = 0
  }

  dialog.addEventListener("close", function () {
    document.documentElement.classList.remove("figure-zoom-open")
    big.removeAttribute("src")
  })
  // any click closes it — on the figure, around it, or on the button
  dialog.addEventListener("click", function () {
    dialog.close()
  })

  images.forEach(function (img) {
    img.addEventListener("click", function () {
      if (img.parentNode.classList.contains("zoomable")) {
        open(img)
      }
    })
  })

  var pending = false
  window.addEventListener("resize", function () {
    if (!pending) {
      pending = true
      requestAnimationFrame(function () {
        pending = false
        mark()
      })
    }
  })
  mark()
  // the side panel (site.js) narrows the column when it arrives; measure again
  if (window.folioPanel) {
    window.folioPanel.then(mark, mark)
  }
})()
