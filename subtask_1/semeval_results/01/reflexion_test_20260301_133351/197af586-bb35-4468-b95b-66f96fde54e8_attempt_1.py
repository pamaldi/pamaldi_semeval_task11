% Facts for spiders and arachnids
spider(spider1).
arachnid(spider1).

% mammal has no facts
mammal(_) :- fail.

% Rule from premise: All spiders are arachnids
arachnid(X) :- spider(X).

% E-premise constraint: No spider is a mammal
conflict :- spider(X), mammal(X).

% O-conclusion: Some arachnids are not mammals
valid_syllogism :- arachnid(X), \+ mammal(X).