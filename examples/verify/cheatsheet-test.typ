// Verifies every construct recommended in the skill's LaTeX→Typst reference compiles on this typst.
#set page(width: 14cm, height: auto, margin: 1cm)
#set text(size: 10pt, lang: "en")
#set par(justify: true, first-line-indent: 1em)
#set heading(numbering: "1.1")
#set math.equation(numbering: "(1)")
#show heading.where(level: 1): set text(fill: blue)
#show link: underline

= Intro <sec:intro>
*bold* _emph_ `raw` #underline[u] #smallcaps[Sc] #text(fill: red, size: 12pt)[red]
#strike[s] #super[sup] #sub[sub] #highlight[hl] #lorem(5)
See @sec:intro and @eq:e, cite @key, #cite(<key>, form: "prose"). Footnote#footnote[note].
#link("https://typst.app")[Typst] -- en–dash --- em—dash, nbsp~here, line \
break. #h(1em) #v(4pt)

- item
  - nested
+ numbered
/ Term: def

$ e = m c^2 $ <eq:e>
$ frac(a, b) + a/b + sqrt(x) + root(3, x) + x^(2n) + x_(i j) + sum_(i=1)^n i + integral_0^1 f(x) dif x $
$ RR, NN, ZZ, QQ, CC, bb(X), cal(A), bold(v), upright(d), italic(x), op("argmax") $
$ alpha beta gamma Gamma, dot.op, times, <=, >=, !=, lt.eq, gt.eq, eq.not, infinity, oo, partial, nabla, dots, dots.c, ->, =>, arrow.r, approx, equiv, subset.eq, in, in.not, forall, exists $
$ hat(x), tilde(x), overline(x), arrow(x), dot(x), macron(x), abs(x), norm(x), floor(x), ceil(x) $
$ lr(( a/b )), mat(1, 2; 3, 4), vec(1, 2), cases(x "if" x > 0, 0 "otherwise") $
$ a &= b + c \
  &= d $
$ "text in math" quad x wide y $

#figure(rect(width: 2cm, height: 1cm), caption: [A figure.]) <fig:a>
#figure(table(columns: 2, align: (left, center), stroke: 0.5pt, table.header[*A*][*B*], [1], [2], table.hline(), [3], [4]), caption: [Table.]) <tab:a>
#grid(columns: (1fr, 2fr), gutter: 6pt, [a], [b])
#align(center)[centered] #box(stroke: 1pt, inset: 3pt)[box] #block(fill: luma(230), inset: 4pt)[block]
#pagebreak(weak: true)
#context counter(heading).display() #context counter(page).get()
#let f(x, y: 2) = x + y
#f(1, y: 3) #for i in range(2) [#i] #if 1 < 2 [yes] else [no]
#bibliography("refs.bib", style: "ieee")
$ binom(n, k) + mat(1, 2; 3, 4, delim: "[") + op("argmax", limits: #true)_x f + a thin b $
#raw("x") #linebreak() #image("dot.svg", width: 1cm)
#text(fill: color.mix(red, blue))[mix] #text(fill: rgb("#1f77b4"))[hex]
#show figure.where(kind: table): set figure.caption(position: top)
#show raw.where(block: true): set block(fill: luma(240))
#show "TODO": text(red)[TODO]
#show: body => body
#let tpl(title: none, body) = { set text(size: 10pt); body }
#show: tpl.with(title: [X])
TODO
