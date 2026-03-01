% Witness: an item that is a shirt and clothing (contradiction will be handled)
shirt(s1).

% Rules from premises
% "Anything that is clothing is not a shirt"
% i.e., If X is clothing, then X cannot be a shirt
% But we need to assert that shirts exist in apparel
% So we need to show that not all apparel is clothing

% "Apparel has members that are shirts"
apparel(s1).

% Validity check: Some apparel is not clothing
% Since all clothing is NOT a shirt, but some apparel is a shirt → those shirts are NOT clothing
valid_syllogism :- apparel(X), \+ clothing(X).

% Fail clause for clothing since no clothing exists
clothing(_) :- fail.