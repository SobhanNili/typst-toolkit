#let report(title: none, author: none, body) = {
  set document(title: title, author: author)
  set page(paper: "a4", margin: (x: 2.2cm, y: 2.5cm), numbering: "1")
  set text(size: 10.5pt, lang: "en")
  set par(justify: true)
  set heading(numbering: "1.1")
  show heading.where(level: 1): it => block(above: 1.6em, below: 1em, text(14pt, it))
  align(center, text(20pt, weight: "bold", title))
  align(center, author)
  v(1em)
  body
}
