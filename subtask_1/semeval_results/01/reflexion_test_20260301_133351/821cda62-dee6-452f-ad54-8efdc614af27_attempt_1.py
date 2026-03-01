% Witness: a shed that is a skyscraper
shed(s1).
skyscraper(s1).

% Rule from A-premise (All skyscrapers are buildings)
building(X) :- skyscraper(X).

% Validity check: All sheds are buildings
valid_syllogism :- \+ (shed(X), \+ building(X)).