% COUNTEREXAMPLE: Some sheds are skyscrapers, and all skyscrapers are buildings
% BUT NOT ALL sheds are buildings

% Witness: a shed that is a skyscraper (s1) and a shed that is NOT a skyscraper (s2)
shed(s1).
shed(s2).
skyscraper(s1).

% A-premise: All skyscrapers are buildings
building(X) :- skyscraper(X).

% Validity check: NOT all sheds are buildings
valid_syllogism :- shed(X), \+ building(X).