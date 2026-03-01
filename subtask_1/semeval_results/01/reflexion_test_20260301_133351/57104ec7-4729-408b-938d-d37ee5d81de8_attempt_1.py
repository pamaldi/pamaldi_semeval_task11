% Witness: a building that is a skyscraper (and thus a tall structure)
building(s1).
skyscraper(s1).

% Rule from premise: a skyscraper is a tall structure
tall_structure(X) :- skyscraper(X).

% Validity check: some tall structures are buildings (I-conclusion)
valid_syllogism :- tall_structure(X), building(X).