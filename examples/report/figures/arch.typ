#import "@preview/cetz:0.3.4": canvas, draw

#canvas({
  import draw: *
  rect((0, 0), (2, 1), name: "a")
  content("a", [Input])
  rect((3, 0), (5, 1), name: "b")
  content("b", [Model])
  line("a.east", "b.west", mark: (end: ">"))
})
