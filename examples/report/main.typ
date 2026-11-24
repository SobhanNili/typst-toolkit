#import "template.typ": report
#show: report.with(title: [A Small Report], author: "Demo Author")

#outline()

#include "chapters/intro.typ"
#include "chapters/results.typ"

#bibliography("refs.bib")
