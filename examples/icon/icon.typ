// Source of the plugin icon: ttk render examples/icon/icon.typ --ppi 144 → 512px square
#set page(width: 256pt, height: 256pt, margin: 0pt, fill: rgb("#239dad"))
#place(center + horizon, box(width: 200pt, height: 200pt, radius: 36pt, fill: white,
  align(center + horizon, stack(spacing: 10pt,
    text(font: "DejaVu Sans", size: 96pt, weight: "bold", fill: rgb("#239dad"))[t],
    text(font: "DejaVu Sans", size: 22pt, fill: rgb("#1b4d55"))[toolkit],
  ))))
