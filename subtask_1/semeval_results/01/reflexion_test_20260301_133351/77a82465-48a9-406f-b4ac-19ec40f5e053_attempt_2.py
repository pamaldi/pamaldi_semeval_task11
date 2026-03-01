% Facts for witness (director who works in production)
director(john).
production_worker(john).

% Rule from A-premise: All filmmakers are production workers
production_worker(X) :- filmmaker(X).

% filmmaker has NO facts, so use fail clause
filmmaker(_) :- fail.

% Validity check: All directors are filmmakers
valid_syllogism :- \+ (director(X), \+ filmmaker(X)).