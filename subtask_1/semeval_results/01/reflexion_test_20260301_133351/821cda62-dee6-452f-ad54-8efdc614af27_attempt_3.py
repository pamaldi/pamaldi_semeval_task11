% COUNTEREXAMPLE: Some sheds are skyscrapers, and all skyscrapers are buildings
% BUT NOT ALL sheds are buildings

% Witness: s1 is a shed and a skyscraper (thus a building)
%          s2 is a shed that is NOT a skyscraper (thus NOT guaranteed to be a building)
shed(s1).
shed(s2).
skyscraper(s1).

% A-premise: All skyscrapers are buildings
building(X) :- skyscraper(X).

% Validity check: Is the conclusion "All sheds are buildings" TRUE?
% We want to show it's FALSE (i.e., find a shed that is NOT a building)
valid_syllogism :- shed(X), \+ building(X).