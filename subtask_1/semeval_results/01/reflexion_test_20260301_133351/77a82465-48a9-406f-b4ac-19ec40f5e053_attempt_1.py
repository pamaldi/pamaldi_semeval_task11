% Facts for witness (director who works in production)
director(john).
production_worker(john).

% Rule from A-premise: All filmmakers are production workers
production_worker(X) :- filmmaker(X).

% Validity check: All directors are filmmakers
valid_syllogism :- \+ (director(X), \+ filmmaker(X)).