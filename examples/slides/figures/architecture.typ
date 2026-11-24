// Static cetz figure, includable from slides or documents.
// Boxes are sized by their labels (content frames) and placed relative to each other,
// so the layout survives any font size.
#import "@preview/cetz:0.5.2"

#cetz.canvas({
  import cetz.draw: *
  let ink = rgb("#23373b")
  let node(pos, name, body, fill: white, anchor: "center") = content(
    pos, body, name: name, anchor: anchor,
    frame: "rect", padding: (x: .45, y: .3), stroke: 1.2pt + ink, fill: fill,
  )
  let gap = 1.6
  node((0, 0), "src", [`.typ` sources], anchor: "west")
  node((rel: (gap, 0), to: "src.east"), "ttk", [compile + lint], fill: rgb("#eb811b").lighten(75%), anchor: "west")
  node((rel: (gap, 0), to: "ttk.east"), "png", [PNG renders], anchor: "west")
  set-style(mark: (end: "stealth", fill: ink), stroke: 1.2pt + ink)
  line("src.east", "ttk.west")
  line("ttk.east", "png.west")
  // feedback loop underneath
  line("png.south", (rel: (0, -1.2)), (rel: (0, -1.2), to: "src.south"), "src.south",
    stroke: (paint: ink, thickness: 1pt, dash: "dashed"))
  content((rel: (0, -1.2), to: "ttk.south"), anchor: "north", padding: .35,
    text(0.75em)[Claude inspects and iterates])
})
